"""Thin wrappers around ffmpeg/ffprobe: thumbnails, duration probing, and the
conversion format table.
"""

import mimetypes
import subprocess
from pathlib import Path

# rounds odd dimensions down to even — libx264 refuses e.g. 1920x1019
_EVEN_SCALE = "scale=trunc(iw/2)*2:trunc(ih/2)*2"

# target extension → (mime type, ffmpeg output args)
CONVERT_FORMATS: dict[str, tuple[str, list[str]]] = {
    "mp4": ("video/mp4", ["-vf", _EVEN_SCALE, "-c:v", "libx264", "-preset", "veryfast",
                          "-crf", "23", "-c:a", "aac", "-movflags", "+faststart"]),
    "webm": ("video/webm", ["-c:v", "libvpx", "-b:v", "1M", "-c:a", "libvorbis"]),
    "gif": ("image/gif", ["-vf", "fps=12,scale=480:-1:flags=lanczos", "-an"]),
    "mp3": ("audio/mpeg", ["-vn", "-c:a", "libmp3lame", "-q:a", "4"]),
    "m4a": ("audio/mp4", ["-vn", "-c:a", "aac"]),
    "wav": ("audio/wav", ["-vn", "-c:a", "pcm_s16le"]),
}
AUDIO_TARGETS = {"mp3", "m4a", "wav"}


def make_thumbnail(path: Path, content_type: str | None, keep_alpha: bool = False) -> str | None:
    """Grab a poster frame for a video/image; None for anything else.

    JPEG by default. `keep_alpha` writes a PNG instead, for sources whose
    transparency is the point — a JPEG thumbnail of a cutout is a black blob.
    """
    kind = (content_type or mimetypes.guess_type(path.name)[0] or "").split("/")[0]
    if kind not in ("video", "image"):
        return None

    thumb = path.parent / f"{path.stem}_thumb.{'png' if keep_alpha else 'jpg'}"
    args = ["ffmpeg", "-y"]
    if kind == "video":
        args += ["-ss", "1"]
    args += ["-i", str(path), "-frames:v", "1", "-vf", "scale=480:-2", str(thumb)]
    try:
        subprocess.run(args, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return str(thumb) if thumb.exists() else None


def probe_duration(path: Path) -> float:
    """Media duration in seconds, or 0.0 if it can't be determined."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        return float(out.stdout.strip())
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0.0
