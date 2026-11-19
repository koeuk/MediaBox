"""Task-lifecycle helpers shared by the download/convert workers:
cooperative cancellation and a single failure path.
"""

import threading

from app.models import Download, DownloadStatus

PAUSED_ERROR = "Paused — press Retry to resume"

_lock = threading.Lock()
_cancel_requests: set[int] = set()


class Cancelled(Exception):
    """Raised inside a worker when the user asked it to stop."""


def request_cancel(download_id: int) -> None:
    """Ask the worker processing this download to stop at its next checkpoint."""
    with _lock:
        _cancel_requests.add(download_id)


def take_cancel(download_id: int) -> bool:
    """Return True once if a stop was requested, clearing the request."""
    with _lock:
        if download_id in _cancel_requests:
            _cancel_requests.discard(download_id)
            return True
        return False


def checkpoint(download_id: int) -> None:
    """Raise Cancelled if a stop was requested for this download."""
    if take_cancel(download_id):
        raise Cancelled()


def mark_failed(db, download_id: int, error: str, mutate=None) -> None:
    """Roll back the session, then flag the record failed with a short message.

    `mutate(dl)` may adjust the record further before commit (e.g. record how
    many bytes survived on disk).
    """
    db.rollback()
    dl = db.get(Download, download_id)
    if dl is None:
        return
    dl.status = DownloadStatus.failed
    dl.error = (error or "")[:500] or "Failed"
    if mutate is not None:
        mutate(dl)
    db.commit()
