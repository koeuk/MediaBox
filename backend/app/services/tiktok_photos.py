"""Download TikTok photo (slideshow) posts.

yt-dlp resolves these posts fine but deliberately treats them as audio-only —
it never turns the slides into formats, so `bv*+ba/b` selects the background
music and you get an m4a instead of the pictures. The images *are* present in
the metadata yt-dlp already fetches, under `imagePost.images[]`, so this module
reuses yt-dlp's web extraction to read them and downloads them itself.

Output depends on the post:
  * one slide   -> the image is saved as-is (the music is dropped)
  * many slides -> an MP4 slideshow muxed with the post's audio, so the result
                   behaves like every other video in the box (preview,
                   thumbnail, convert) instead of a pile of loose files
"""

import mimetypes
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.models import DownloadStatus
from app.services import ffmpeg, storage
from app.services.ssrf import ensure_public_host
from app.services.tasks import checkpoint

# canvas bounds for the rendered slideshow; slides are letterboxed to fit
MAX_W, MAX_H = 1080, 1920
# per-slide screen time, and the window we squeeze it into when there's audio
DEFAULT_SLIDE_SECONDS = 3.0
MIN_SLIDE_SECONDS, MAX_SLIDE_SECONDS = 2.0, 8.0

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


def _canvas(sizes: list[tuple[int, int]]) -> tuple[int, int]:
    """An even-dimensioned canvas that fits the largest slide within bounds."""
    width = max((w for w, _ in sizes if w), default=0) or MAX_W
    height = max((h for _, h in sizes if h), default=0) or MAX_H
    scale = min(MAX_W / width, MAX_H / height, 1.0)
    # libx264 with yuv420p requires even dimensions
    return max(2, int(width * scale) // 2 * 2), max(2, int(height * scale) // 2 * 2)


def _render_slideshow(
    images: list[Path], audio: Path | None, sizes: list[tuple[int, int]], dest: Path
) -> None:
    """Mux the slides (and audio, if any) into an MP4."""
    width, height = _canvas(sizes)

    seconds = DEFAULT_SLIDE_SECONDS
    if audio:
        duration = ffmpeg.probe_duration(audio)
        if duration:
            seconds = min(max(duration / len(images), MIN_SLIDE_SECONDS), MAX_SLIDE_SECONDS)

    args = ["ffmpeg", "-y"]
    for image in images:
        args += ["-loop", "1", "-t", f"{seconds:.3f}", "-i", str(image)]
    if audio:
        args += ["-i", str(audio)]

    fit = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p"
    )
    steps = [f"[{i}:v]{fit}[v{i}]" for i in range(len(images))]
    steps.append(
        "".join(f"[v{i}]" for i in range(len(images)))
        + f"concat=n={len(images)}:v=1:a=0[v]"
    )
    if audio:
        # apad + -shortest makes the audio exactly match the slideshow whether
        # the track is longer or shorter than the slides
        steps.append(f"[{len(images)}:a]apad[a]")

    args += ["-filter_complex", ";".join(steps), "-map", "[v]"]
    if audio:
        args += ["-map", "[a]", "-c:a", "aac", "-b:a", "128k", "-shortest"]
    args += [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dest),
    ]

    result = subprocess.run(args, capture_output=True, timeout=600)
    if result.returncode != 0 or not dest.exists() or not dest.stat().st_size:
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        raise ValueError(
            "Could not build the slideshow video"
            + (f": {detail[-1][:200]}" if detail else "")
        )


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

    sizes = [
        (image.get("imageWidth") or 0, image.get("imageHeight") or 0)
        for image in (data.get("imagePost") or {}).get("images") or []
    ]
    audio_url = (data.get("music") or {}).get("playUrl")
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
                # slides are ~85% of the work; the render is the rest
                dl.progress = round((index + 1) / len(slides) * 85, 1)
                dl.downloaded_bytes = downloaded
                dl.total_bytes = downloaded
                db.commit()

            audio: Path | None = None
            if audio_url and len(images) > 1:
                try:
                    audio = tmp / "audio.m4a"
                    downloaded += _download(client, [audio_url], audio, limit - downloaded)
                except ValueError:
                    audio = None  # a silent slideshow beats no slideshow

        checkpoint(dl.id)

        if len(images) == 1:
            # a single-slide post is just a picture — keep it as one
            suffix = mimetypes.guess_extension(
                mimetypes.guess_type(str(images[0]))[0] or "image/jpeg"
            ) or ".jpg"
            dest = storage.new_path(dl.user_id, f"{title[:80]}{suffix}")
            dest.write_bytes(images[0].read_bytes())
            content_type = "image/jpeg"
        else:
            dl.progress = 90.0
            db.commit()
            dest = storage.new_path(dl.user_id, f"{title[:80]}.mp4")
            _render_slideshow(images, audio, sizes, dest)
            content_type = "video/mp4"

    size = dest.stat().st_size
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
