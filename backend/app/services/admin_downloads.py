"""Permanent admin deletion, with per-record results for retrying storage failures."""

import logging

from sqlalchemy.exc import SQLAlchemyError

from app.models import Download
from app.schemas.admin import AdminDownloadDeleteFailure, AdminDownloadsDeleteResult
from app.services import jobs, storage
from app.services.object_store import StorageError
from app.services.tasks import request_cancel, take_cancel

logger = logging.getLogger(__name__)
STOP_TIMEOUT_SECONDS = 2


def delete(db, ids: list[int]) -> AdminDownloadsDeleteResult:
    deleted = []
    failed = []
    for ident in dict.fromkeys(ids):
        lock = jobs.download_lock(ident)
        # A queued worker may start immediately after this read. Sending cancel
        # for every record closes that race; the marker is cleared under lock.
        request_cancel(ident)
        if not lock.acquire(timeout=STOP_TIMEOUT_SECONDS):
            failed.append(AdminDownloadDeleteFailure(
                id=ident, detail="Job is still stopping. Try deleting it again shortly.",
            ))
            continue
        try:
            # Discard a stale transaction before reading paths produced by a
            # worker that just stopped/completed while we waited for its lock.
            db.rollback()
            dl = db.get(Download, ident)
            generation = dl.job_token if dl is not None else None
            if dl is not None:
                storage.delete_files(dl.file_path, dl.thumbnail_path, *dl.slide_paths)
                db.delete(dl)
                db.commit()
            if generation:
                jobs.discard_pending(ident, generation)
            deleted.append(ident)  # Already absent is an idempotent success.
        except (StorageError, OSError, SQLAlchemyError):
            db.rollback()
            logger.warning("Admin could not permanently delete download %s", ident)
            failed.append(AdminDownloadDeleteFailure(
                id=ident, detail="Could not delete this download. Please retry.",
            ))
        finally:
            take_cancel(ident)
            lock.release()
    return AdminDownloadsDeleteResult(deleted_ids=deleted, failed=failed)
