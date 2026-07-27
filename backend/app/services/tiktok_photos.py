"""Download TikTok photo (slideshow) posts.

yt-dlp resolves these posts fine but deliberately treats them as audio-only —
it never turns the slides into formats, so `bv*+ba/b` selects the background
music and you get an m4a instead of the pictures. The images *are* present in
the metadata yt-dlp already fetches, under `imagePost.images[]`, so this module
reuses yt-dlp's web extraction to read them and downloads them itself.

The slides are kept as images, mirroring what the post is on TikTok: every
image is saved and the record carries the ordered list in `Download.slides`,
which the preview steps through as a slider. `file_path` points at slide 1, so
the thumbnail, Save and card paths behave like any other image.

The post's background music is dropped — there is no video to carry it.
"""

import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.models import DownloadStatus
from app.services import ffmpeg, storage
from app.services.ssrf import ensure_public_host
from app.services.tasks import checkpoint

_PHOTO_PATH_RE = re.compile(r"^/@[\w.-]+/photo/(\d+)")
_TIMEOUT = httpx.Timeout(30.0, read=120.0)
_HEADERS = {
    # the CDN 403s without a TikTok referer
    "Referer": "https://www.tiktok.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
}


def photo_post_id(url: str) -> str | None:
    """The aweme id for a …/@user/photo/<id> URL, else None."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not (host == "tiktok.com" or host.endswith(".tiktok.com")):
        return None
    match = _PHOTO_PATH_RE.match(parsed.path)
    return match.group(1) if match else None


def _fetch_post_data(url: str, video_id: str) -> dict:
    """Pull the post's metadata using yt-dlp's own web extractor.

    Coupled to two yt-dlp internals (`TikTokIE._extract_web_data_and_status`
    and the `imagePost` shape). That is deliberate: they handle the headers,
    cookies and universal-data parsing that make the request succeed at all,
    and re-implementing that here would rot faster than it does.
    """
    import yt_dlp
    from yt_dlp.extractor.tiktok import TikTokIE

    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "no_color": True}) as ydl:
        extractor = TikTokIE(ydl)
        extractor.initialize()
        # /photo/ isn't in TikTokIE._VALID_URL, but the /video/ form of the
        # same id serves identical metadata
        video_url = re.sub(r"/photo/(\d+)", r"/video/\1", url)
        data, status = extractor._extract_web_data_and_status(video_url, video_id, fatal=False)

    if status == 10204:
        raise ValueError("TikTok is blocking this server's IP from viewing the post")
    if status in (10216, 10222):
        raise ValueError("This post is private")
    if not data:
        raise ValueError(f"Could not read this post from TikTok (status {status})")
    return data


def _slide_urls(data: dict) -> list[list[str]]:
    """Mirror lists for each slide, best-quality field first."""
    slides = []
    for image in (data.get("imagePost") or {}).get("images") or []:
        urls = (image.get("imageURL") or {}).get("urlList") or []
        if urls:
            slides.append(list(urls))
    return slides


def _download(client: httpx.Client, mirrors: list[str], dest: Path, limit: int) -> int:
    """Save the first mirror that works. Returns bytes written."""
    last_error: Exception | None = None
    for url in mirrors:
        try:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()
                size = 0
                with open(dest, "wb") as fh:
                    for chunk in resp.iter_bytes(256 * 1024):
                        size += len(chunk)
                        if size > limit:
                            raise ValueError("Post exceeds the size limit")
                        fh.write(chunk)
                if size:
                    return size
        except ValueError:
            raise
        except Exception as exc:  # try the next mirror
            last_error = exc
            dest.unlink(missing_ok=True)
    raise ValueError(f"Could not download a slide ({last_error})")


def run_photo_post(dl, db, url: str | None = None) -> None:
    """Fetch a TikTok photo post onto `dl`, tracking progress as it goes."""
    source = url or dl.url
    video_id = photo_post_id(source)
    if not video_id:
        raise ValueError("Not a TikTok photo post URL")

    data = _fetch_post_data(source, video_id)
    slides = _slide_urls(data)
    if not slides:
        raise ValueError("TikTok returned no images for this post")

    title = (data.get("desc") or "").strip() or f"TikTok photo {video_id}"
    limit = storage.max_bytes()

    dl.total_bytes = 0
    dl.downloaded_bytes = 0
    db.commit()

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        downloaded = 0

        with httpx.Client(
            follow_redirects=True,
            timeout=_TIMEOUT,
            headers=_HEADERS,
            event_hooks={"request": [ensure_public_host]},
        ) as client:
            images: list[Path] = []
            for index, mirrors in enumerate(slides):
                checkpoint(dl.id)
                path = tmp / f"slide_{index:03d}.jpg"
                downloaded += _download(client, mirrors, path, limit - downloaded)
                images.append(path)
                dl.progress = round((index + 1) / len(slides) * 95, 1)
                dl.downloaded_bytes = downloaded
                dl.total_bytes = downloaded
                db.commit()

        checkpoint(dl.id)

        # staged in the temp dir first: a slide that fails partway through
        # would otherwise leave orphans in the user's folder
        stored: list[Path] = []
        multi = len(images) > 1
        for index, image in enumerate(images):
            name = f"{title[:70]} {index + 1:02d}.jpg" if multi else f"{title[:80]}.jpg"
            dest = storage.new_path(dl.user_id, name)
            dest.write_bytes(image.read_bytes())
            stored.append(dest)

    first = stored[0]
    size = sum(path.stat().st_size for path in stored)
    dl.title = dl.title or title
    dl.filename = first.name.split("_", 1)[-1]
    dl.file_path = str(first)
    dl.slides = json.dumps([str(p) for p in stored]) if multi else None
    dl.content_type = "image/jpeg"
    dl.total_bytes = size
    dl.downloaded_bytes = size
    dl.progress = 100.0
    dl.thumbnail_path = ffmpeg.make_thumbnail(first, "image/jpeg")
    dl.status = DownloadStatus.completed
    dl.completed_at = datetime.now(timezone.utc)
    db.commit()
