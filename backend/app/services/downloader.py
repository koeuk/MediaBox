import ipaddress
import mimetypes
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

from app.config import settings
from app.database import SessionLocal
from app.models import Download, DownloadStatus

CHUNK_SIZE = 256 * 1024
PERSIST_EVERY_BYTES = 1024 * 1024

PAUSED_ERROR = "Paused — press Retry to resume"

# strips terminal color escapes yt-dlp puts in error strings
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

_cancel_lock = threading.Lock()
_cancel_requests: set[int] = set()


class _Cancelled(Exception):
    pass


def request_cancel(download_id: int) -> None:
    """Ask the worker processing this download to stop at the next checkpoint."""
    with _cancel_lock:
        _cancel_requests.add(download_id)


def _take_cancel(download_id: int) -> bool:
    with _cancel_lock:
        if download_id in _cancel_requests:
            _cancel_requests.discard(download_id)
            return True
        return False

# rounds odd dimensions down to even — libx264 refuses e.g. 1920x1019
EVEN_SCALE = "scale=trunc(iw/2)*2:trunc(ih/2)*2"

# target → (mime type, ffmpeg output args)
CONVERT_FORMATS: dict[str, tuple[str, list[str]]] = {
    "mp4": ("video/mp4", ["-vf", EVEN_SCALE,
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                          "-c:a", "aac", "-movflags", "+faststart"]),
    "webm": ("video/webm", ["-c:v", "libvpx", "-b:v", "1M", "-c:a", "libvorbis"]),
    "gif": ("image/gif", ["-vf", "fps=12,scale=480:-1:flags=lanczos", "-an"]),
    "mp3": ("audio/mpeg", ["-vn", "-c:a", "libmp3lame", "-q:a", "4"]),
    "m4a": ("audio/mp4", ["-vn", "-c:a", "aac"]),
    "wav": ("audio/wav", ["-vn", "-c:a", "pcm_s16le"]),
}
AUDIO_TARGETS = {"mp3", "m4a", "wav"}


def _is_ytdlp_url(url: str) -> bool:
    """True when the URL's host is on the extractor allowlist (TikTok, Facebook, …)."""
    host = (urlparse(url).hostname or "").lower()
    for item in settings.ytdlp_hosts.split(","):
        item = item.strip().lower()
        if item and (host == item or host.endswith(f".{item}")):
            return True
    return False


def _run_ytdlp(dl: Download, db) -> None:
    """Fetch a video from a supported site with yt-dlp, tracking progress.

    Page URLs (TikTok, Facebook, …) can't be streamed directly — yt-dlp
    resolves the actual media, downloads it, and merges streams via ffmpeg.
    """
    import yt_dlp  # heavy import, only needed on this path

    user_dir = settings.media_dir / str(dl.user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    prefix = uuid.uuid4().hex[:8]

    last_write = 0.0
    cancelled = False

    def hook(d: dict) -> None:
        nonlocal last_write, cancelled
        if _take_cancel(dl.id):
            cancelled = True
            raise _Cancelled()
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

    if dl.quality:
        fmt = f"bv*[height<={dl.quality}]+ba/b[height<={dl.quality}]"
    else:
        fmt = "bv*+ba/b"
    opts = {
        "outtmpl": str(user_dir / f"{prefix}_%(title).80B.%(ext)s"),
        "format": fmt,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "max_filesize": settings.max_download_size_mb * 1024 * 1024,
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
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(dl.url, download=True)
    except _Cancelled:
        raise
    except Exception as exc:
        # yt-dlp may wrap the hook's cancel exception in its own error type
        if cancelled:
            raise _Cancelled() from None
        if isinstance(exc, yt_dlp.utils.DownloadError):
            message = _ANSI_RE.sub("", str(exc)).replace("ERROR: ", "").strip()
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
    dl.thumbnail_path = _make_thumbnail(path, content_type)
    dl.status = DownloadStatus.completed
    dl.completed_at = datetime.now(timezone.utc)
    db.commit()


def _ensure_public_host(request: httpx.Request) -> None:
    """Block requests to private/internal addresses (SSRF guard).

    Runs as an httpx event hook so every hop of a redirect chain is checked,
    not just the URL the user submitted.
    """
    if settings.allow_private_urls:
        return
    host = request.url.host
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        raise ValueError(f"Could not resolve host {host!r}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ValueError(
                "This URL points to a private or internal address and cannot be downloaded"
            )


def _filename_from_response(url: str, response: httpx.Response) -> str:
    disposition = response.headers.get("content-disposition", "")
    match = re.search(r'filename="?([^";]+)"?', disposition)
    if match:
        return Path(unquote(match.group(1))).name
    name = Path(unquote(urlparse(url).path)).name
    return name or "download"


def _make_thumbnail(path: Path, content_type: str | None) -> str | None:
    kind = (content_type or mimetypes.guess_type(path.name)[0] or "").split("/")[0]
    if kind not in ("video", "image"):
        return None

    thumb = path.parent / f"{path.stem}_thumb.jpg"
    args = ["ffmpeg", "-y"]
    if kind == "video":
        args += ["-ss", "1"]
    args += ["-i", str(path), "-frames:v", "1", "-vf", "scale=480:-2", str(thumb)]
    try:
        subprocess.run(args, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return str(thumb) if thumb.exists() else None


def run_download(download_id: int, resume: bool = False) -> None:
    """Stream a URL to disk, persisting progress so the UI can follow it.

    With resume=True and a partial file on disk, ask the server for the
    remaining bytes via a Range request; a 200 response restarts from zero.
    """
    db = SessionLocal()
    try:
        dl = db.get(Download, download_id)
        if dl is None:
            return
        if _take_cancel(download_id):
            raise _Cancelled()

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

        if _is_ytdlp_url(dl.url):
            _run_ytdlp(dl, db)
            return

        max_bytes = settings.max_download_size_mb * 1024 * 1024
        timeout = httpx.Timeout(30.0, read=120.0)
        headers = {"Range": f"bytes={start_at}-"} if start_at else {}
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            event_hooks={"request": [_ensure_public_host]},
        ) as client:
            with client.stream("GET", dl.url, headers=headers) as resp:
                resp.raise_for_status()

                if start_at and resp.status_code != 206:
                    start_at = 0  # server ignored the Range header

                remaining = int(resp.headers.get("content-length") or 0)
                total = start_at + remaining if remaining else 0
                content_range = resp.headers.get("content-range", "")
                if "/" in content_range:
                    try:
                        total = int(content_range.rsplit("/", 1)[1])
                    except ValueError:
                        pass
                if total > max_bytes:
                    raise ValueError(
                        f"File exceeds the {settings.max_download_size_mb} MB limit"
                    )

                content_type = (resp.headers.get("content-type") or "").split(";")[0].strip()
                # a web page is not a media file — fail loudly instead of saving junk HTML
                page_types = ("text/html", "application/xhtml+xml")
                wants_html = urlparse(dl.url).path.lower().endswith((".html", ".htm"))
                if content_type in page_types and not wants_html:
                    raise ValueError(
                        "This link is a web page, not a media file. Use a direct file URL "
                        "(one ending in .mp4, .mp3, .jpg, …) or a TikTok/Facebook video link."
                    )
                filename = dl.filename or _filename_from_response(dl.url, resp)

                if dest is None:
                    user_dir = settings.media_dir / str(dl.user_id)
                    user_dir.mkdir(parents=True, exist_ok=True)
                    dest = user_dir / f"{uuid.uuid4().hex[:8]}_{filename}"

                dl.total_bytes = total
                dl.content_type = content_type or None
                dl.filename = filename
                # persist the path up front so a failed attempt can be resumed
                dl.file_path = str(dest)
                db.commit()

                done = start_at
                last_persisted = start_at
                with open(dest, "ab" if start_at else "wb") as fh:
                    for chunk in resp.iter_bytes(CHUNK_SIZE):
                        fh.write(chunk)
                        done += len(chunk)
                        if _take_cancel(download_id):
                            raise _Cancelled()
                        if done > max_bytes:
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
        dl.thumbnail_path = _make_thumbnail(dest, dl.content_type)
        dl.status = DownloadStatus.completed
        dl.completed_at = datetime.now(timezone.utc)
        db.commit()
    except _Cancelled:
        db.rollback()
        # the partial file stays on disk; /retry resumes it via HTTP Range
        dl = db.get(Download, download_id)
        if dl is not None:
            dl.status = DownloadStatus.failed
            dl.error = PAUSED_ERROR
            if dl.file_path and Path(dl.file_path).exists():
                dl.downloaded_bytes = Path(dl.file_path).stat().st_size
            db.commit()
    except Exception as exc:
        db.rollback()
        # the partial file is kept on disk so /retry can resume it
        dl = db.get(Download, download_id)
        if dl is not None:
            dl.status = DownloadStatus.failed
            dl.error = str(exc)[:500] or exc.__class__.__name__
            db.commit()
    finally:
        db.close()


def _probe_duration(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        return float(out.stdout.strip())
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0.0


def run_convert(download_id: int, source_path: str, target: str) -> None:
    """Convert an existing media file with FFmpeg into a new Download record,
    tracking progress via ffmpeg's -progress output against the source duration."""
    db = SessionLocal()
    out_path: Path | None = None
    try:
        dl = db.get(Download, download_id)
        if dl is None:
            return
        if _take_cancel(download_id):
            raise _Cancelled()
        dl.status = DownloadStatus.downloading
        db.commit()

        source = Path(source_path)
        if not source.exists():
            raise ValueError("Source file is missing")
        mime, codec_args = CONVERT_FORMATS[target]
        duration = _probe_duration(source)

        base = source.stem.split("_", 1)[-1] if "_" in source.stem else source.stem
        filename = f"{Path(base).stem}.{target}"
        out_path = source.parent / f"{uuid.uuid4().hex[:8]}_{filename}"

        # stderr goes to a temp file so a failure can report ffmpeg's actual error
        stderr_file = tempfile.TemporaryFile()
        proc = subprocess.Popen(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-i", str(source), *codec_args,
             "-progress", "pipe:1", "-nostats", str(out_path)],
            stdout=subprocess.PIPE, stderr=stderr_file, text=True,
        )
        last_progress = 0.0
        assert proc.stdout is not None
        for line in proc.stdout:
            if _take_cancel(download_id):
                proc.kill()
                proc.wait(timeout=30)
                raise _Cancelled()
            if duration and line.startswith("out_time_ms="):
                try:
                    seconds = int(line.split("=", 1)[1]) / 1_000_000
                except ValueError:
                    continue
                progress = min(round(seconds / duration * 100, 1), 99.9)
                if progress - last_progress >= 2:
                    last_progress = progress
                    dl.progress = progress
                    db.commit()
        proc.wait(timeout=3600)
        if proc.returncode != 0 or not out_path.exists():
            stderr_file.seek(0)
            detail = stderr_file.read().decode(errors="replace").strip()[-350:]
            raise RuntimeError(
                f"FFmpeg conversion failed: {detail}" if detail else "FFmpeg conversion failed"
            )

        size = out_path.stat().st_size
        dl.filename = filename
        dl.file_path = str(out_path)
        dl.content_type = mime
        dl.total_bytes = size
        dl.downloaded_bytes = size
        dl.progress = 100.0
        dl.thumbnail_path = _make_thumbnail(out_path, mime)
        dl.status = DownloadStatus.completed
        dl.completed_at = datetime.now(timezone.utc)
        db.commit()
    except _Cancelled:
        db.rollback()
        # a half-written conversion is useless — remove it
        if out_path is not None:
            out_path.unlink(missing_ok=True)
        dl = db.get(Download, download_id)
        if dl is not None:
            dl.status = DownloadStatus.failed
            dl.error = "Stopped — press Retry to convert again"
            db.commit()
    except Exception as exc:
        db.rollback()
        if out_path is not None:
            out_path.unlink(missing_ok=True)
        dl = db.get(Download, download_id)
        if dl is not None:
            dl.status = DownloadStatus.failed
            dl.error = str(exc)[:500] or exc.__class__.__name__
            db.commit()
    finally:
        db.close()
