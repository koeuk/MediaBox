"""Fetch videos from sites that don't expose direct file URLs (TikTok,
Facebook, YouTube) using yt-dlp.
"""

import mimetypes
import re
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from app.config import settings
from app.models import DownloadStatus
from app.services import ffmpeg, storage
from app.services.tasks import Cancelled, take_cancel
from app.services.tiktok_photos import photo_post_id

# strips terminal color escapes yt-dlp puts in error strings
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def is_ytdlp_url(url: str) -> bool:
    """True when the URL's host is on the extractor allowlist (subdomains included)."""
    host = (urlparse(url).hostname or "").lower()
    for item in settings.ytdlp_hosts.split(","):
        item = item.strip().lower()
        if item and (host == item or host.endswith(f".{item}")):
            return True
    return False


def is_tiktok_photo_url(url: str) -> bool:
    """True for TikTok photo/slideshow posts (…/@user/photo/<id>).

    These need app.services.tiktok_photos instead of yt-dlp: the extractor
    only matches /video/ and /embed/, and even under /video/ it treats a
    slideshow as audio-only, so downloading it here saves the background music
    rather than the pictures.
    """
    return photo_post_id(url) is not None


# a short link only reveals it points at a photo post once yt-dlp has followed
# the redirect and failed on the resolved URL
_UNSUPPORTED_PHOTO_RE = re.compile(r"Unsupported URL:\s*(\S*/photo/\d+\S*)")


def _build_opts(dl, out_template: str, hook) -> dict:
    fmt = (
        f"bv*[height<={dl.quality}]+ba/b[height<={dl.quality}]"
        if dl.quality
        else "bv*+ba/b"
    )
    opts = {
        "outtmpl": out_template,
        "format": fmt,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "max_filesize": storage.max_bytes(),
        "progress_hooks": [hook],
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "no_color": True,  # keep ANSI escapes out of error messages
        "retries": 5,
        "fragment_retries": 5,
    }
    if settings.ytdlp_cookies_file:
        opts["cookiefile"] = settings.ytdlp_cookies_file
    # YouTube needs a JavaScript runtime for full format extraction
    runtimes = {name: {"path": None} for name in ("deno", "node", "bun") if shutil.which(name)}
    if runtimes:
        opts["js_runtimes"] = runtimes
    # solver components stop YouTube throttling downloads to a crawl
    components = [c.strip() for c in settings.ytdlp_remote_components.split(",") if c.strip()]
    if components:
        opts["remote_components"] = components
    return opts


def run_ytdlp(dl, db) -> None:
    """Resolve and download a video with yt-dlp, tracking progress on `dl`.

    Page URLs (TikTok, Facebook, …) can't be streamed directly — yt-dlp
    resolves the media, downloads it, and merges streams via ffmpeg.
    """
    import yt_dlp  # heavy import, only needed on this path

    out_dir = storage.user_dir(dl.user_id)
    out_template = str(out_dir / f"{uuid.uuid4().hex[:8]}_%(title).80B.%(ext)s")

    last_write = 0.0
    cancelled = False

    def hook(d: dict) -> None:
        nonlocal last_write, cancelled
        if take_cancel(dl.id):
            cancelled = True
            raise Cancelled()
        if d.get("status") != "downloading":
            return
        now = time.monotonic()
        if now - last_write < 1.0:
            return
        last_write = now
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        dl.downloaded_bytes = d.get("downloaded_bytes") or 0
        dl.total_bytes = total
        if total:
            dl.progress = min(round(dl.downloaded_bytes / total * 100, 1), 99.9)
        db.commit()

    try:
        with yt_dlp.YoutubeDL(_build_opts(dl, out_template, hook)) as ydl:
            info = ydl.extract_info(dl.url, download=True)
    except Cancelled:
        raise
    except Exception as exc:
        # yt-dlp may wrap the hook's cancel exception in its own error type
        if cancelled:
            raise Cancelled() from None
        if isinstance(exc, yt_dlp.utils.DownloadError):
            message = _ANSI_RE.sub("", str(exc)).replace("ERROR: ", "").strip()
            # a short link that turned out to be a photo post: retry it on the
            # slideshow path now that the redirect has given us the real URL
            resolved = _UNSUPPORTED_PHOTO_RE.search(message)
            if resolved and is_tiktok_photo_url(resolved.group(1)):
                from app.services.tiktok_photos import run_photo_post

                run_photo_post(dl, db, url=resolved.group(1))
                return
            raise ValueError(f"Could not fetch this video: {message}") from exc
        raise

    requested = (info or {}).get("requested_downloads") or []
    path = Path(requested[0]["filepath"]) if requested else None
    if path is None or not path.exists():
        raise ValueError("The video could not be saved (no file produced)")

    size = path.stat().st_size
    content_type = mimetypes.guess_type(path.name)[0] or "video/mp4"
    dl.title = dl.title or info.get("title") or path.stem
    dl.filename = path.name.split("_", 1)[-1]
    dl.file_path = str(path)
    dl.content_type = content_type
    dl.total_bytes = size
    dl.downloaded_bytes = size
    dl.progress = 100.0
    dl.thumbnail_path = ffmpeg.make_thumbnail(path, content_type)
    dl.status = DownloadStatus.completed
    dl.completed_at = datetime.now(timezone.utc)
    db.commit()
