"""Stream a direct media URL to disk with resumable, progress-tracked writes.

Non-direct URLs (TikTok/Facebook/YouTube) are handed off to the yt-dlp
extractor; everything else is streamed here over HTTP.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

from app.config import settings
from app.database import SessionLocal
from app.models import Download, DownloadStatus
from app.services import ffmpeg, storage
from app.services.extractor import is_tiktok_photo_url, is_ytdlp_url, run_ytdlp
from app.services.tiktok_photos import run_photo_post
from app.services.ssrf import ensure_public_host
from app.services.tasks import Cancelled, PAUSED_ERROR, checkpoint, mark_failed

CHUNK_SIZE = 256 * 1024
PERSIST_EVERY_BYTES = 1024 * 1024

_PAGE_TYPES = ("text/html", "application/xhtml+xml")


def _filename_from_response(url: str, response: httpx.Response) -> str:
    disposition = response.headers.get("content-disposition", "")
    match = re.search(r'filename="?([^";]+)"?', disposition)
    if match:
        return Path(unquote(match.group(1))).name
    name = Path(unquote(urlparse(url).path)).name
    return name or "download"


def _total_size(response: httpx.Response, start_at: int) -> int:
    """Best guess at the full size from Content-Length / Content-Range."""
    remaining = int(response.headers.get("content-length") or 0)
    total = start_at + remaining if remaining else 0
    content_range = response.headers.get("content-range", "")
    if "/" in content_range:
        try:
            total = int(content_range.rsplit("/", 1)[1])
        except ValueError:
            pass
    return total


def _reject_web_page(url: str, content_type: str) -> None:
    """Fail loudly on an HTML page so we never save junk instead of media."""
    wants_html = urlparse(url).path.lower().endswith((".html", ".htm"))
    if content_type in _PAGE_TYPES and not wants_html:
        raise ValueError(
            "This link is a web page, not a media file. Use a direct file URL "
            "(one ending in .mp4, .mp3, .jpg, …) or a TikTok/Facebook video link."
        )


def run_download(download_id: int, resume: bool = False) -> None:
    """Stream a URL to disk, persisting progress so the UI can follow it.

    With resume=True and a partial file on disk, ask for the remaining bytes via
    a Range request; a 200 response restarts from zero.
    """
    db = SessionLocal()
    try:
        dl = db.get(Download, download_id)
        if dl is None:
            return
        checkpoint(download_id)

        dest: Path | None = None
        start_at = 0
        if resume and dl.file_path and Path(dl.file_path).exists():
            dest = Path(dl.file_path)
            start_at = dest.stat().st_size

        dl.status = DownloadStatus.downloading
        dl.error = None
        db.commit()

        if not dl.url.lower().startswith(("http://", "https://")):
            raise ValueError(
                "This item has no downloadable URL — convert again from the source card"
            )
        # photo posts need their own path — yt-dlp only yields their audio
        if is_tiktok_photo_url(dl.url):
            run_photo_post(dl, db)
            return
        if is_ytdlp_url(dl.url):
            run_ytdlp(dl, db)
            return

        limit = storage.max_bytes()
        timeout = httpx.Timeout(30.0, read=120.0)
        headers = {"Range": f"bytes={start_at}-"} if start_at else {}
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            event_hooks={"request": [ensure_public_host]},
        ) as client:
            with client.stream("GET", dl.url, headers=headers) as resp:
                resp.raise_for_status()
                if start_at and resp.status_code != 206:
                    start_at = 0  # server ignored the Range header

                total = _total_size(resp, start_at)
                if total > limit:
                    raise ValueError(f"File exceeds the {settings.max_download_size_mb} MB limit")

                content_type = (resp.headers.get("content-type") or "").split(";")[0].strip()
                _reject_web_page(dl.url, content_type)
                filename = dl.filename or _filename_from_response(dl.url, resp)

                if dest is None:
                    dest = storage.new_path(dl.user_id, filename)

                dl.total_bytes = total
                dl.content_type = content_type or None
                dl.filename = filename
                dl.file_path = str(dest)  # persist up front so a failure can resume
                db.commit()

                done = start_at
                last_persisted = start_at
                with open(dest, "ab" if start_at else "wb") as fh:
                    for chunk in resp.iter_bytes(CHUNK_SIZE):
                        fh.write(chunk)
                        done += len(chunk)
                        checkpoint(download_id)
                        if done > limit:
                            raise ValueError(
                                f"File exceeds the {settings.max_download_size_mb} MB limit"
                            )
                        if done - last_persisted >= PERSIST_EVERY_BYTES:
                            last_persisted = done
                            dl.downloaded_bytes = done
                            if total:
                                dl.progress = round(done / total * 100, 1)
                            db.commit()

        dl.downloaded_bytes = done
        dl.total_bytes = total or done
        dl.progress = 100.0
        if not dl.title:
            dl.title = filename
        dl.thumbnail_path = ffmpeg.make_thumbnail(dest, dl.content_type)
        dl.status = DownloadStatus.completed
        dl.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Cancelled:
        # the partial file stays on disk; /retry resumes it via HTTP Range
        def keep_partial(dl: Download) -> None:
            if dl.file_path and Path(dl.file_path).exists():
                dl.downloaded_bytes = Path(dl.file_path).stat().st_size

        mark_failed(db, download_id, PAUSED_ERROR, mutate=keep_partial)
    except Exception as exc:
        # the partial file is kept on disk so /retry can resume it
        mark_failed(db, download_id, str(exc) or exc.__class__.__name__)
    finally:
        db.close()
