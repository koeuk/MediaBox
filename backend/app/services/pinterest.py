"""Download Pinterest pins — video, image, or GIF — including pin.it links.

yt-dlp's Pinterest extractor only builds formats from `videos.video_list`, so
it handles video pins and fails with "no video formats" on the image and GIF
pins that make up most of the site. The pictures are right there in the same
API response under `images`, so this module fetches the pin once, then either
hands the video off to yt-dlp or saves the image itself.
"""

import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.models import DownloadStatus
from app.services import ffmpeg, storage
from app.services.ssrf import ensure_public_host
from app.services.tasks import checkpoint

# pinterest.com, pinterest.co.uk, br.pinterest.com, … — the TLD list is long
# and keeps growing, so match the label rather than enumerate it
_PIN_HOST_RE = re.compile(r"(?:^|\.)pinterest\.[a-z.]{2,7}$")
_PIN_PATH_RE = re.compile(r"^/pin/(?:[\w-]+--)?(\d+)")
_SHORT_HOSTS = {"pin.it"}

# biggest first — 'orig' is the untouched upload, the rest are Pinterest's
# resized renditions used as a fallback when it is missing
_IMAGE_PREFERENCE = ("orig", "736x", "600x315", "564x", "474x", "236x", "170x")

_TIMEOUT = httpx.Timeout(30.0, read=120.0)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
}


def is_pinterest_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in _SHORT_HOSTS or bool(_PIN_HOST_RE.search(host))


def _is_short_link(url: str) -> bool:
    return (urlparse(url).hostname or "").lower() in _SHORT_HOSTS


def pin_id(url: str) -> str | None:
    """The numeric pin id for a /pin/<id> URL, else None."""
    parsed = urlparse(url)
    if not _PIN_HOST_RE.search((parsed.hostname or "").lower()):
        return None
    match = _PIN_PATH_RE.match(parsed.path)
    return match.group(1) if match else None


def resolve_share_link(url: str) -> str:
    """Follow a pin.it short link to the canonical pin URL."""
    with httpx.Client(
        follow_redirects=True,
        timeout=_TIMEOUT,
        headers=_HEADERS,
        event_hooks={"request": [ensure_public_host]},
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return str(resp.url)


def _fetch_pin(video_id: str) -> dict:
    """Pin metadata via yt-dlp's Pinterest API helper.

    Coupled to `PinterestBaseIE._call_api`, which supplies the endpoint and
    the header Pinterest requires; the response itself is plain JSON.
    """
    import yt_dlp
    from yt_dlp.extractor.pinterest import PinterestIE

    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "no_color": True}) as ydl:
        extractor = PinterestIE(ydl)
        extractor.initialize()
        response = extractor._call_api(
            "Pin", video_id, {"field_set_key": "unauth_react_main_pin", "id": video_id}
        )
    data = (response or {}).get("data")
    if not isinstance(data, dict):
        raise ValueError("Pinterest did not return this pin — it may be private or deleted")
    return data


def _best_image(data: dict) -> str | None:
    """URL of the largest usable rendition."""
    images = data.get("images")
    if not isinstance(images, dict):
        return None

    def usable(key):
        value = images.get(key)
        return value if isinstance(value, dict) and value.get("url") else None

    preferred = [usable(key) for key in _IMAGE_PREFERENCE]
    # anything Pinterest adds that isn't in the preference list, largest first
    extras = sorted(
        (v for k, v in images.items()
         if k not in _IMAGE_PREFERENCE and isinstance(v, dict) and v.get("url")),
        key=lambda v: (v.get("width") or 0) * (v.get("height") or 0),
        reverse=True,
    )
    for image in [*(p for p in preferred if p), *extras]:
        return image["url"]
    return None


def _has_video(data: dict) -> bool:
    for path in (("videos", "video_list"), ("story_pin_data", "pages")):
        node = data
        for key in path:
            node = (node or {}).get(key) if isinstance(node, dict) else None
        if node:
            return True
    return bool((data.get("embed") or {}).get("src"))


def _download_image(url: str, dest: Path, limit: int) -> tuple[int, str]:
    """Stream an image to disk. Returns (bytes, content_type)."""
    with httpx.Client(
        follow_redirects=True,
        timeout=_TIMEOUT,
        headers={**_HEADERS, "Referer": "https://www.pinterest.com/"},
        event_hooks={"request": [ensure_public_host]},
    ) as client:
        with client.stream("GET", url) as resp:
            resp.raise_for_status()
            content_type = (resp.headers.get("content-type") or "").split(";")[0].strip()
            size = 0
            with open(dest, "wb") as fh:
                for chunk in resp.iter_bytes(256 * 1024):
                    size += len(chunk)
                    if size > limit:
                        raise ValueError("This pin exceeds the size limit")
                    fh.write(chunk)

    if not size:
        raise ValueError("Pinterest returned an empty file")
    if not content_type.startswith("image/"):
        content_type = mimetypes.guess_type(dest.name)[0] or "image/jpeg"
    return size, content_type


def run_pinterest(dl, db) -> None:
    """Fetch a Pinterest pin onto `dl`, picking the video or image path."""
    from app.services.extractor import run_ytdlp

    url = dl.url
    if _is_short_link(url):
        url = resolve_share_link(url)

    video_id = pin_id(url)
    if not video_id:
        raise ValueError(
            "Only single Pinterest pins can be downloaded — that link looks "
            "like a board or profile."
        )

    checkpoint(dl.id)
    data = _fetch_pin(video_id)
    canonical = f"https://www.pinterest.com/pin/{video_id}/"

    # video pins are yt-dlp's job — it handles the HLS renditions properly
    if _has_video(data):
        run_ytdlp(dl, db, url=canonical)
        return

    image_url = _best_image(data)
    if not image_url:
        raise ValueError("This pin has no downloadable image or video")

    title = (
        (data.get("title") or data.get("grid_title") or "").strip()
        or f"Pinterest pin {video_id}"
    )
    suffix = Path(urlparse(image_url).path).suffix.lower() or ".jpg"
    if suffix not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        suffix = ".jpg"

    dest = storage.new_path(dl.user_id, f"{title[:80]}{suffix}")
    try:
        size, content_type = _download_image(image_url, dest, storage.max_bytes())
    except Exception:
        dest.unlink(missing_ok=True)
        raise

    dl.title = dl.title or title
    dl.filename = dest.name.split("_", 1)[-1]
    dl.file_path = str(dest)
    dl.content_type = content_type
    dl.total_bytes = size
    dl.downloaded_bytes = size
    dl.progress = 100.0
    dl.thumbnail_path = ffmpeg.make_thumbnail(dest, content_type)
    dl.status = DownloadStatus.completed
    dl.completed_at = datetime.now(timezone.utc)
    db.commit()
