"""Convert an existing media file to another format with ffmpeg, tracking
progress against the source duration.
"""

import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.database import SessionLocal
from app.models import Download, DownloadStatus
from app.services import ffmpeg, storage
from app.services.tasks import Cancelled, checkpoint, mark_failed, take_cancel


def run_convert(download_id: int, source_path: str, target: str) -> None:
    """Convert `source_path` into a new file for the given Download record."""
    db = SessionLocal()
    out_path: Path | None = None
    try:
        dl = db.get(Download, download_id)
        if dl is None:
            return
        checkpoint(download_id)
        dl.status = DownloadStatus.downloading
        db.commit()

        source = Path(source_path)
        if not source.exists():
            raise ValueError("Source file is missing")
        mime, codec_args = ffmpeg.CONVERT_FORMATS[target]
        duration = ffmpeg.probe_duration(source)

        base = source.stem.split("_", 1)[-1] if "_" in source.stem else source.stem
        filename = f"{Path(base).stem}.{target}"
        out_path = storage.new_path(dl.user_id, filename)

        # stderr → temp file so a failure can report ffmpeg's actual error
        stderr_file = tempfile.TemporaryFile()
        proc = subprocess.Popen(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-i", str(source), *codec_args, "-progress", "pipe:1", "-nostats", str(out_path)],
            stdout=subprocess.PIPE, stderr=stderr_file, text=True,
        )

        last_progress = 0.0
        assert proc.stdout is not None
        for line in proc.stdout:
            if take_cancel(download_id):
                proc.kill()
                proc.wait(timeout=30)
                raise Cancelled()
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
        dl.thumbnail_path = ffmpeg.make_thumbnail(out_path, mime)
        dl.status = DownloadStatus.completed
        dl.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Cancelled:
        # a half-written conversion is useless — remove it
        if out_path is not None:
            out_path.unlink(missing_ok=True)
        mark_failed(db, download_id, "Stopped — press Retry to convert again")
    except Exception as exc:
        if out_path is not None:
            out_path.unlink(missing_ok=True)
        mark_failed(db, download_id, str(exc) or exc.__class__.__name__)
    finally:
        db.close()
