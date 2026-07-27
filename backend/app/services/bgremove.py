"""Remove the background from an image, writing a transparent PNG.

Uses rembg (ONNX U^2-Net family) on the CPU. The model files are not shipped —
rembg downloads the one a quality tier needs on first use into ~/.u2net and
reuses it afterwards, so the very first cutout at a given quality is slow.
"""

import threading
from datetime import datetime, timezone
from pathlib import Path

from app.database import SessionLocal
from app.models import Download, DownloadStatus
from app.services import ffmpeg, storage
from app.services.tasks import Cancelled, checkpoint, mark_failed

# quality → (rembg model, alpha matting)
#
# Alpha matting refines the cut along soft edges (hair, fur, motion blur) at a
# noticeable CPU cost, so it is reserved for the top tier.
#
# Tier names are kept to four characters because they are stored in the
# downloads.quality column, which is VARCHAR(8).
QUALITY_MODELS: dict[str, tuple[str, bool]] = {
    "fast": ("u2netp", False),
    "good": ("u2net", False),
    "best": ("isnet-general-use", True),
}
DEFAULT_QUALITY = "good"

# Sessions hold an ONNX runtime instance and are expensive to build, so keep
# one per model. Guarded because several workers can ask for one at once.
_sessions: dict[str, object] = {}
_sessions_lock = threading.Lock()


def _session(model_name: str):
    with _sessions_lock:
        if model_name not in _sessions:
            from rembg import new_session

            _sessions[model_name] = new_session(model_name)
        return _sessions[model_name]


def run_remove_bg(download_id: int, source_path: str, quality: str) -> None:
    """Cut the subject out of `source_path` into a new transparent PNG."""
    from rembg import remove

    db = SessionLocal()
    out_path: Path | None = None
    try:
        dl = db.get(Download, download_id)
        if dl is None:
            return
        checkpoint(download_id)
        dl.status = DownloadStatus.downloading
        dl.progress = 5.0
        db.commit()

        source = Path(source_path)
        if not source.exists():
            raise ValueError("Source image is missing")

        model_name, alpha_matting = QUALITY_MODELS.get(
            quality, QUALITY_MODELS[DEFAULT_QUALITY]
        )

        # Fetching the model can take a while on a cold cache; hold the bar at
        # 10% so the card doesn't look stalled at 5%.
        dl.progress = 10.0
        db.commit()
        session = _session(model_name)

        checkpoint(download_id)
        dl.progress = 35.0
        db.commit()

        data = source.read_bytes()
        # rembg mirrors its input type, so bytes in → PNG bytes out
        cut = remove(
            data,
            session=session,
            alpha_matting=alpha_matting,
            post_process_mask=True,
            force_return_bytes=True,
        )

        checkpoint(download_id)
        dl.progress = 90.0
        db.commit()

        base = source.stem.split("_", 1)[-1] if "_" in source.stem else source.stem
        filename = f"{Path(base).stem}-nobg.png"
        out_path = storage.new_path(dl.user_id, filename)
        out_path.write_bytes(cut)

        size = out_path.stat().st_size
        dl.filename = filename
        dl.file_path = str(out_path)
        dl.content_type = "image/png"
        dl.total_bytes = size
        dl.downloaded_bytes = size
        dl.progress = 100.0
        dl.thumbnail_path = ffmpeg.make_thumbnail(out_path, "image/png", keep_alpha=True)
        dl.status = DownloadStatus.completed
        dl.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Cancelled:
        # a half-written cutout is useless — remove it
        if out_path is not None:
            out_path.unlink(missing_ok=True)
        mark_failed(db, download_id, "Stopped — press Retry to run it again")
    except Exception as exc:
        if out_path is not None:
            out_path.unlink(missing_ok=True)
        mark_failed(db, download_id, str(exc) or exc.__class__.__name__)
    finally:
        db.close()
