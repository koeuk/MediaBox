"""Bounded worker pool for downloads and conversions.

FastAPI's BackgroundTasks runs jobs on the request threadpool, so a burst of
large downloads could starve the API of threads. Jobs submitted here wait in
a queue (status stays "queued") until one of a fixed number of daemon workers
picks them up. Daemon threads mean shutdown never blocks on an in-flight
download — partial files are resumable via /retry.
"""

import queue
import threading
from weakref import WeakValueDictionary

from app.config import settings

_jobs: queue.Queue = queue.Queue()
_start_lock = threading.Lock()
_started = False
_record_locks = WeakValueDictionary()
_record_locks_guard = threading.Lock()
_pending: dict[int, dict[threading.Event, str]] = {}


def download_lock(download_id: int):
    """Serialize worker execution and permanent deletion for the same record.

    Weak references let idle locks disappear when neither caller uses them.
    Like the queue, this guard belongs to the single API process.
    """
    with _record_locks_guard:
        lock = _record_locks.get(download_id)
        if lock is None:
            lock = threading.RLock()
            _record_locks[download_id] = lock
        return lock


def _worker() -> None:
    while True:
        fn, args, ticket, generation = _jobs.get()
        try:
            with download_lock(args[0]):
                # Deletion invalidates each queued invocation, including one
                # already dequeued but still waiting for the record lock.
                if not ticket.is_set() and _matches_generation(args[0], generation):
                    fn(*args)
        except Exception:
            # run_download/run_convert record their own failures; a worker
            # thread must survive anything that slips through
            pass
        finally:
            with _record_locks_guard:
                tickets = _pending.get(args[0])
                if tickets is not None:
                    tickets.pop(ticket, None)
                    if not tickets:
                        _pending.pop(args[0], None)
            _jobs.task_done()


def discard_pending(download_id: int, generation: str) -> None:
    """Invalidate old invocations independently of a possibly reused DB ID."""
    with _record_locks_guard:
        tickets = _pending.get(download_id, {})
        for ticket, token in list(tickets.items()):
            if token == generation:
                ticket.set()
                tickets.pop(ticket)
        if not tickets:
            _pending.pop(download_id, None)


def _matches_generation(download_id: int, generation: str) -> bool:
    from sqlalchemy import select
    from app.database import SessionLocal
    from app.models import Download

    with SessionLocal() as db:
        current = db.scalar(select(Download.job_token).where(Download.id == download_id))
    return bool(generation and current == generation)


def submit(fn, *args, generation: str) -> None:
    global _started
    with _start_lock:
        if not _started:
            for i in range(settings.max_concurrent_downloads):
                threading.Thread(
                    target=_worker, daemon=True, name=f"mediabox-worker-{i}"
                ).start()
            _started = True
    ticket = threading.Event()
    with _record_locks_guard:
        _pending.setdefault(args[0], {})[ticket] = generation
    _jobs.put((fn, args, ticket, generation))


def reset_interrupted() -> None:
    """Fail any download left mid-flight by a previous process.

    The queue is in-memory, so a restart forgets in-progress work; marking it
    failed lets the user resume it with /retry instead of it hanging forever.
    """
    from app.database import SessionLocal
    from app.models import Download, DownloadStatus

    db = SessionLocal()
    try:
        stuck = (
            db.query(Download)
            .filter(Download.status.in_([DownloadStatus.queued, DownloadStatus.downloading]))
            .all()
        )
        for dl in stuck:
            dl.status = DownloadStatus.failed
            dl.error = "Interrupted by a server restart — retry to resume"
        db.commit()
    finally:
        db.close()
