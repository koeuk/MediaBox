"""Bounded worker pool for downloads and conversions.

FastAPI's BackgroundTasks runs jobs on the request threadpool, so a burst of
large downloads could starve the API of threads. Jobs submitted here wait in
a queue (status stays "queued") until one of a fixed number of daemon workers
picks them up. Daemon threads mean shutdown never blocks on an in-flight
download — partial files are resumable via /retry.
"""

import queue
import threading

from app.config import settings

_jobs: queue.Queue = queue.Queue()
_start_lock = threading.Lock()
_started = False


def _worker() -> None:
    while True:
        fn, args = _jobs.get()
        try:
            fn(*args)
        except Exception:
            # run_download/run_convert record their own failures; a worker
            # thread must survive anything that slips through
            pass
        finally:
            _jobs.task_done()


def submit(fn, *args) -> None:
    global _started
    with _start_lock:
        if not _started:
            for i in range(settings.max_concurrent_downloads):
                threading.Thread(
                    target=_worker, daemon=True, name=f"mediabox-worker-{i}"
                ).start()
            _started = True
    _jobs.put((fn, args))


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
