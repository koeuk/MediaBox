import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_media_user
from app.database import get_db
from app.models import Download, DownloadStatus, User
from app.schemas import BatchDownloadCreate, ConvertRequest, DownloadCreate, DownloadOut
from app.config import settings
from app.services import jobs
from app.services.downloader import (
    AUDIO_TARGETS,
    _make_thumbnail,
    request_cancel,
    run_convert,
    run_download,
)

router = APIRouter()


def _get_owned(download_id: int, db: Session, user: User) -> Download:
    dl = db.get(Download, download_id)
    if dl is None or dl.user_id != user.id:
        raise HTTPException(status_code=404, detail="Download not found")
    return dl


@router.post("", response_model=DownloadOut, status_code=status.HTTP_201_CREATED)
def create_download(
    payload: DownloadCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dl = Download(
        user_id=user.id, url=str(payload.url), title=payload.title, quality=payload.quality
    )
    db.add(dl)
    db.commit()
    db.refresh(dl)
    jobs.submit(run_download, dl.id)
    return dl


@router.post("/batch", response_model=list[DownloadOut], status_code=status.HTTP_201_CREATED)
def create_batch(
    payload: BatchDownloadCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    records = [
        Download(user_id=user.id, url=str(url), quality=payload.quality) for url in payload.urls
    ]
    db.add_all(records)
    db.commit()
    for dl in records:
        db.refresh(dl)
        jobs.submit(run_download, dl.id)
    return records


@router.post("/upload", response_model=DownloadOut, status_code=status.HTTP_201_CREATED)
def upload_media(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Save a local media file as a completed download so it can be
    previewed and converted like anything else in the box."""
    filename = Path(file.filename or "upload").name
    content_type = (file.content_type or "").split(";")[0].strip()
    if not content_type or content_type == "application/octet-stream":
        content_type = mimetypes.guess_type(filename)[0] or ""
    if not content_type.startswith(("video/", "audio/", "image/")):
        raise HTTPException(status_code=400, detail="Only video, audio, or image files can be uploaded")

    user_dir = settings.media_dir / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / f"{uuid.uuid4().hex[:8]}_{filename}"

    max_bytes = settings.max_download_size_mb * 1024 * 1024
    size = 0
    try:
        with open(dest, "wb") as fh:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the {settings.max_download_size_mb} MB limit",
                    )
                fh.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise

    dl = Download(
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
        thumbnail_path=_make_thumbnail(dest, content_type),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(dl)
    db.commit()
    db.refresh(dl)
    return dl


@router.get("", response_model=list[DownloadOut])
def list_downloads(
    search: str | None = None,
    favorites: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Download).filter(Download.user_id == user.id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Download.title.ilike(like), Download.filename.ilike(like), Download.url.ilike(like))
        )
    if favorites:
        query = query.filter(Download.is_favorite.is_(True))
    return query.order_by(Download.created_at.desc()).all()


@router.get("/{download_id}", response_model=DownloadOut)
def get_download(
    download_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _get_owned(download_id, db, user)


@router.patch("/{download_id}/favorite", response_model=DownloadOut)
def toggle_favorite(
    download_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dl = _get_owned(download_id, db, user)
    dl.is_favorite = not dl.is_favorite
    db.commit()
    db.refresh(dl)
    return dl


@router.post("/{download_id}/retry", response_model=DownloadOut)
def retry_download(
    download_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dl = _get_owned(download_id, db, user)
    if dl.status != DownloadStatus.failed:
        raise HTTPException(status_code=409, detail="Only failed downloads can be retried")

    is_conversion = bool(dl.convert_source and dl.convert_target)
    if is_conversion and not Path(dl.convert_source).exists():
        raise HTTPException(
            status_code=409, detail="The source file is gone — convert again from its card"
        )
    if not is_conversion and dl.url.startswith("upload://"):
        raise HTTPException(
            status_code=409,
            detail="This item can't be re-fetched — convert again from the source card",
        )

    dl.status = DownloadStatus.queued
    dl.error = None
    db.commit()
    db.refresh(dl)
    if is_conversion:
        jobs.submit(run_convert, dl.id, dl.convert_source, dl.convert_target)
    else:
        jobs.submit(run_download, dl.id, True)
    return dl


@router.post("/{download_id}/cancel", response_model=DownloadOut)
def cancel_download(
    download_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Stop an active download/conversion at its next checkpoint.

    The record turns failed with a "Paused" note; direct downloads keep their
    partial file and Retry resumes via HTTP Range."""
    dl = _get_owned(download_id, db, user)
    if dl.status not in (DownloadStatus.queued, DownloadStatus.downloading):
        raise HTTPException(status_code=409, detail="Only active downloads can be stopped")
    request_cancel(dl.id)
    return dl


@router.post("/{download_id}/convert", response_model=DownloadOut, status_code=status.HTTP_201_CREATED)
def convert_download(
    download_id: int,
    payload: ConvertRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dl = _get_owned(download_id, db, user)
    if dl.status != DownloadStatus.completed or not dl.file_path or not Path(dl.file_path).exists():
        raise HTTPException(status_code=409, detail="Source file is not available")

    kind = (dl.content_type or "").split("/")[0]
    if kind not in ("video", "audio"):
        raise HTTPException(status_code=400, detail="Only video or audio files can be converted")
    if kind == "audio" and payload.target not in AUDIO_TARGETS:
        raise HTTPException(status_code=400, detail="Audio files can only convert to mp3, m4a, or wav")

    base = (dl.title or dl.filename or "media").rsplit(".", 1)[0]
    record = Download(
        user_id=user.id,
        url=dl.url,
        title=f"{base} ({payload.target})",
        convert_source=dl.file_path,
        convert_target=payload.target,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    jobs.submit(run_convert, record.id, dl.file_path, payload.target)
    return record


@router.delete("/{download_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_download(
    download_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dl = _get_owned(download_id, db, user)
    for path in (dl.file_path, dl.thumbnail_path):
        if path:
            Path(path).unlink(missing_ok=True)
    db.delete(dl)
    db.commit()


@router.get("/{download_id}/file")
def download_file(
    download_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_media_user),
):
    dl = _get_owned(download_id, db, user)
    if (
        dl.status != DownloadStatus.completed
        or not dl.file_path
        or not Path(dl.file_path).exists()
    ):
        raise HTTPException(status_code=404, detail="File not available")
    return FileResponse(
        dl.file_path,
        filename=dl.filename or "download",
        media_type=dl.content_type or "application/octet-stream",
    )


@router.get("/{download_id}/thumbnail")
def download_thumbnail(
    download_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_media_user),
):
    dl = _get_owned(download_id, db, user)
    if not dl.thumbnail_path or not Path(dl.thumbnail_path).exists():
        raise HTTPException(status_code=404, detail="Thumbnail not available")
    return FileResponse(dl.thumbnail_path, media_type="image/jpeg")
