"""Everything that creates or re-queues a Download row.

The routers stay thin HTTP adapters: they translate a `LibraryError` into a
status code and otherwise just hand the request over. Keeping row creation in
one module means "what can put something in the box, and under what rules" has
a single answer.
"""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models import Download, DownloadStatus, User
from app.services import ffmpeg, jobs, storage
from app.services.converter import run_convert
from app.services.downloader import run_download


class LibraryError(Exception):
    """A rejection worth showing the user. `status` is the HTTP code to send."""

    status = 400

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        if status is not None:
            self.status = status


class Conflict(LibraryError):
    """The record exists but its current state forbids the operation."""

    status = 409


class TooLarge(LibraryError):
    status = 413


def _persist(db: Session, dl: Download) -> Download:
    db.add(dl)
    db.commit()
    db.refresh(dl)
    return dl


def queue_download(
    db: Session, user: User, url: str, title: str | None = None, quality: str | None = None
) -> Download:
    dl = _persist(db, Download(user_id=user.id, url=url, title=title, quality=quality))
    jobs.submit(run_download, dl.id)
    return dl


def queue_batch(db: Session, user: User, urls: list[str], quality: str | None) -> list[Download]:
    records = [Download(user_id=user.id, url=url, quality=quality) for url in urls]
    db.add_all(records)
    db.commit()
    for dl in records:
        db.refresh(dl)
        jobs.submit(run_download, dl.id)
    return records


def store_upload(db: Session, user: User, file: UploadFile) -> Download:
    """Save a local media file as a completed download so it can be previewed
    and converted like anything else in the box."""
    try:
        dest, size, content_type = storage.save_upload(file, user.id)
    except storage.UploadTooLarge as exc:
        raise TooLarge(str(exc)) from exc
    except ValueError as exc:
        raise LibraryError(str(exc)) from exc

    filename = dest.name.split("_", 1)[-1]
    return _persist(
        db,
        Download(
            user_id=user.id,
            url=f"upload://{filename}",
            title=Path(filename).stem,
            filename=filename,
            status=DownloadStatus.completed,
            progress=100.0,
            total_bytes=size,
            downloaded_bytes=size,
            content_type=content_type,
            file_path=str(dest),
            thumbnail_path=ffmpeg.make_thumbnail(dest, content_type),
            completed_at=datetime.now(timezone.utc),
        ),
    )


def queue_conversion(db: Session, user: User, source: Download, target: str) -> Download:
    """Queue a new record that transcodes `source` into `target`."""
    if (
        source.status != DownloadStatus.completed
        or not source.file_path
        or not Path(source.file_path).exists()
    ):
        raise Conflict("Source file is not available")

    kind = (source.content_type or "").split("/")[0]
    if kind not in ("video", "audio"):
        raise LibraryError("Only video or audio files can be converted")
    if kind == "audio" and target not in ffmpeg.AUDIO_TARGETS:
        raise LibraryError("Audio files can only convert to mp3, m4a, or wav")

    base = (source.title or source.filename or "media").rsplit(".", 1)[0]
    record = _persist(
        db,
        Download(
            user_id=user.id,
            url=source.url,
            title=f"{base} ({target})",
            convert_source=source.file_path,
            convert_target=target,
        ),
    )
    jobs.submit(run_convert, record.id, source.file_path, target)
    return record


def requeue(db: Session, dl: Download) -> Download:
    """Re-run a failed download or conversion.

    A conversion needs its source file to still be on disk; an upload has no
    URL to re-fetch, so it can only be redone from the card it came from.
    """
    if dl.status != DownloadStatus.failed:
        raise Conflict("Only failed downloads can be retried")

    is_conversion = bool(dl.convert_source and dl.convert_target)
    if is_conversion and not Path(dl.convert_source).exists():
        raise Conflict("The source file is gone — convert again from its card")
    if not is_conversion and dl.url.startswith("upload://"):
        raise Conflict("This item can't be re-fetched — convert again from the source card")

    dl.status = DownloadStatus.queued
    dl.error = None
    db.commit()
    db.refresh(dl)

    if is_conversion:
        jobs.submit(run_convert, dl.id, dl.convert_source, dl.convert_target)
    else:
        jobs.submit(run_download, dl.id, True)
    return dl
