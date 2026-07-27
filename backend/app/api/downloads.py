from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession, MediaUser, owned_or_404
from app.models import Download, DownloadStatus, User
from app.schemas import (
    BatchDownloadCreate,
    ConvertRequest,
    DownloadCategoryUpdate,
    DownloadCreate,
    DownloadOut,
    RemoveBackgroundRequest,
)
from app.services import library, storage
from app.services.tasks import request_cancel

router = APIRouter()

# library.LibraryError subclasses carry their own status code and are turned
# into a {"detail": …} response by the handler registered in app.main.


def _owned(db: Session, download_id: int, user: User) -> Download:
    return owned_or_404(db, Download, download_id, user, "Download")


@router.post("", response_model=DownloadOut, status_code=status.HTTP_201_CREATED)
def create_download(payload: DownloadCreate, db: DbSession, user: CurrentUser):
    return library.queue_download(db, user, str(payload.url), payload.title, payload.quality)


@router.post("/batch", response_model=list[DownloadOut], status_code=status.HTTP_201_CREATED)
def create_batch(payload: BatchDownloadCreate, db: DbSession, user: CurrentUser):
    return library.queue_batch(db, user, [str(u) for u in payload.urls], payload.quality)


@router.post("/upload", response_model=DownloadOut, status_code=status.HTTP_201_CREATED)
def upload_media(
    db: DbSession,
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
    scope: str | None = None,
):
    """`scope=cutout` files belong to the background-removal page only."""
    return library.store_upload(db, user, file, scope=scope)


@router.get("", response_model=list[DownloadOut])
def list_downloads(
    db: DbSession,
    user: CurrentUser,
    search: str | None = None,
    favorites: bool = False,
    category: str | None = None,
):
    query = db.query(Download).filter(Download.user_id == user.id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Download.title.ilike(like), Download.filename.ilike(like), Download.url.ilike(like))
        )
    if favorites:
        query = query.filter(Download.is_favorite.is_(True))
    if category:
        query = query.filter(Download.category == category)
    return query.order_by(Download.created_at.desc()).all()


@router.get("/{download_id}", response_model=DownloadOut)
def get_download(download_id: int, db: DbSession, user: CurrentUser):
    return _owned(db, download_id, user)


@router.patch("/{download_id}/favorite", response_model=DownloadOut)
def toggle_favorite(download_id: int, db: DbSession, user: CurrentUser):
    dl = _owned(db, download_id, user)
    dl.is_favorite = not dl.is_favorite
    db.commit()
    db.refresh(dl)
    return dl


@router.patch("/{download_id}/category", response_model=DownloadOut)
def update_category(
    download_id: int, payload: DownloadCategoryUpdate, db: DbSession, user: CurrentUser
):
    dl = _owned(db, download_id, user)
    dl.category = payload.category
    db.commit()
    db.refresh(dl)
    return dl


@router.post("/{download_id}/retry", response_model=DownloadOut)
def retry_download(download_id: int, db: DbSession, user: CurrentUser):
    return library.requeue(db, _owned(db, download_id, user))


@router.post("/{download_id}/cancel", response_model=DownloadOut)
def cancel_download(download_id: int, db: DbSession, user: CurrentUser):
    """Stop an active download/conversion at its next checkpoint.

    The record turns failed with a "Paused" note; direct downloads keep their
    partial file and Retry resumes via HTTP Range."""
    dl = _owned(db, download_id, user)
    if dl.status not in (DownloadStatus.queued, DownloadStatus.downloading):
        raise HTTPException(status_code=409, detail="Only active downloads can be stopped")
    request_cancel(dl.id)
    return dl


@router.post(
    "/{download_id}/convert", response_model=DownloadOut, status_code=status.HTTP_201_CREATED
)
def convert_download(
    download_id: int, payload: ConvertRequest, db: DbSession, user: CurrentUser
):
    source = _owned(db, download_id, user)
    return library.queue_conversion(db, user, source, payload.target)


@router.post(
    "/{download_id}/remove-background",
    response_model=DownloadOut,
    status_code=status.HTTP_201_CREATED,
)
def remove_background(
    download_id: int, payload: RemoveBackgroundRequest, db: DbSession, user: CurrentUser
):
    """Queue a transparent-PNG cutout of an image already in the box."""
    source = _owned(db, download_id, user)
    return library.queue_cutout(db, user, source, payload.quality)


@router.delete("/{download_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_download(download_id: int, db: DbSession, user: CurrentUser):
    dl = _owned(db, download_id, user)
    storage.delete_files(dl.file_path, dl.thumbnail_path)
    db.delete(dl)
    db.commit()


@router.get("/{download_id}/file")
def download_file(download_id: int, db: DbSession, user: MediaUser):
    dl = _owned(db, download_id, user)
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
def download_thumbnail(download_id: int, db: DbSession, user: MediaUser):
    dl = _owned(db, download_id, user)
    if not dl.thumbnail_path or not Path(dl.thumbnail_path).exists():
        raise HTTPException(status_code=404, detail="Thumbnail not available")
    # cutout thumbnails are PNG so their transparency survives
    kind = "image/png" if dl.thumbnail_path.endswith(".png") else "image/jpeg"
    return FileResponse(dl.thumbnail_path, media_type=kind)
