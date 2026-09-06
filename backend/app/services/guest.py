"""Anonymous, throwaway downloads for visitors who have not signed up.

Deliberately does NOT go through `library`/`downloader`: those persist a
`Download` row, write into a user's media folder, and keep the file around for
the library UI. A guest has no account and no library, so the file exists only
long enough to be handed to their browser and is then deleted along with its
temporary folder.

The trade for that simplicity is that a guest download is synchronous — there
is no job row to poll for progress — so it holds the request open until the
file is ready.
"""

import shutil
import tempfile
import threading
import time
from pathlib import Path

import httpx

from app.config import settings
from app.services import storage
from app.services.extractor import _tiktok_ua, is_ytdlp_url
from app.services.ssrf import ensure_public_host

# Guests pick from these only. Members keep the full ladder (1080p, Best);
# holding anonymous traffic to low quality keeps an open endpoint from being
# a cheap way to pull large files through someone else's server.
GUEST_QUALITIES = ("720", "480")
DEFAULT_QUALITY = "480"

# A guest download costs real bandwidth and disk, so cap how often one caller
# may start another.
RATE_LIMIT = 5
RATE_WINDOW_SECONDS = 600

# In-memory, therefore per-process and reset by a restart. Enough to stop
# casual hammering; a public deployment behind several workers wants a shared
# store (Redis, or the reverse proxy's own limiter) instead.
_hits: dict[str, list[float]] = {}
_hits_lock = threading.Lock()


class GuestError(Exception):
    """Anything the visitor can fix by changing their input."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def check_rate_limit(client_ip: str) -> None:
    now = time.monotonic()
    cutoff = now - RATE_WINDOW_SECONDS
    with _hits_lock:
        recent = [t for t in _hits.get(client_ip, []) if t > cutoff]
        if len(recent) >= RATE_LIMIT:
            raise GuestError(
                "Too many downloads from this address. Try again later, "
                "or sign up for an account.",
                status=429,
            )
        recent.append(now)
        _hits[client_ip] = recent
        # opportunistic sweep so the dict does not grow without bound
        if len(_hits) > 1000:
            for ip in [k for k, v in _hits.items() if not [t for t in v if t > cutoff]]:
                _hits.pop(ip, None)


def normalise_quality(quality: str | None) -> str:
    if quality is None:
        return DEFAULT_QUALITY
    if quality not in GUEST_QUALITIES:
        raise GuestError(
            f"Guests can download at {' or '.join(GUEST_QUALITIES)}p. "
            "Sign in for higher quality."
        )
    return quality


def _largest_file(folder: Path) -> Path | None:
    files = [p for p in folder.rglob("*") if p.is_file()]
    return max(files, key=lambda p: p.stat().st_size) if files else None


def _fetch_direct(url: str, folder: Path) -> Path:
    """A plain media URL — stream it to disk, refusing anything oversized."""
    limit = storage.max_bytes()
    with httpx.Client(
        follow_redirects=True,
        timeout=httpx.Timeout(30.0, read=120.0),
        event_hooks={"request": [ensure_public_host]},
    ) as client:
        with client.stream("GET", url) as resp:
            resp.raise_for_status()
            content_type = (resp.headers.get("content-type") or "").split(";")[0].strip()
            if content_type.startswith("text/html"):
                raise GuestError("That link is a web page, not a media file.")

            name = Path(httpx.URL(url).path).name or "download"
            dest = folder / name
            written = 0
            with open(dest, "wb") as fh:
                for chunk in resp.iter_bytes(1024 * 256):
                    fh.write(chunk)
                    written += len(chunk)
                    if written > limit:
                        raise GuestError(
                            f"File exceeds the {settings.max_download_size_mb} MB limit."
                        )
    return dest


def _fetch_ytdlp(url: str, folder: Path, quality: str) -> Path:
    import yt_dlp

    # Capped by height, and never "best" — the ladder members get does not
    # apply here. The `/b[...]` fallback covers sites offering only muxed files.
    fmt = f"bv*[height<={quality}]+ba/b[height<={quality}]/wv*+ba/w"
    opts = {
        "outtmpl": str(folder / "%(title).80s.%(ext)s"),
        "format": fmt,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "max_filesize": storage.max_bytes(),
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "no_color": True,
        "retries": 3,
        "fragment_retries": 3,
        # same rotation the member path uses; TikTok blocks a fixed fingerprint
        "http_headers": {"User-Agent": _tiktok_ua(1)},
    }
    if settings.ytdlp_cookies_file:
        opts["cookiefile"] = settings.ytdlp_cookies_file

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)

    produced = _largest_file(folder)
    if produced is None:
        raise GuestError("Nothing could be downloaded from that link.")
    return produced


def fetch(url: str, quality: str | None) -> tuple[Path, Path]:
    """Download `url` into a fresh temp folder.

    Returns `(file, folder)` — the caller streams the file and must delete the
    folder afterwards.
    """
    quality = normalise_quality(quality)
    folder = Path(tempfile.mkdtemp(prefix="mediabox-guest-"))
    try:
        if is_ytdlp_url(url):
            path = _fetch_ytdlp(url, folder, quality)
        else:
            path = _fetch_direct(url, folder)
        if path.stat().st_size == 0:
            raise GuestError("The download came back empty.")
        return path, folder
    except GuestError:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        raise GuestError(str(exc) or exc.__class__.__name__) from exc
