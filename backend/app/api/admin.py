from datetime import datetime, timezone

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import func

from app.api.deps import AdminUser, DbSession
from app.security import hash_password
from app.services import storage
from app.models import Download, DownloadStatus, Review, User
from app.schemas import (
    AdminDownloadOut,
    AdminStats,
    AdminUserEdit,
    AdminUserOut,
    ReviewCreate,
    ReviewEdit,
    ReviewOut,
)

router = APIRouter()


@router.get("/stats", response_model=AdminStats)
def stats(db: DbSession, _: AdminUser):
    by_status = dict(
        db.query(Download.status, func.count(Download.id)).group_by(Download.status).all()
    )
    return AdminStats(
        users=db.query(func.count(User.id)).scalar() or 0,
        downloads=db.query(func.count(Download.id)).scalar() or 0,
        reviews=db.query(func.count(Review.id)).scalar() or 0,
        queued=by_status.get(DownloadStatus.queued, 0),
        downloading=by_status.get(DownloadStatus.downloading, 0),
        completed=by_status.get(DownloadStatus.completed, 0),
        failed=by_status.get(DownloadStatus.failed, 0),
        favorites=db.query(func.count(Download.id)).filter(Download.is_favorite.is_(True)).scalar() or 0,
        bytes_stored=db.query(func.coalesce(func.sum(Download.downloaded_bytes), 0))
        .filter(Download.status == DownloadStatus.completed)
        .scalar()
        or 0,
    )


@router.get("/users", response_model=list[AdminUserOut])
def list_users(db: DbSession, _: AdminUser):
    rows = (
        db.query(
            User,
            func.count(Download.id),
            func.coalesce(func.sum(Download.downloaded_bytes), 0),
        )
        .outerjoin(Download, Download.user_id == User.id)
        .group_by(User.id)
        .order_by(User.created_at.asc())
        .all()
    )
    return [
        AdminUserOut(
            id=user.id,
            email=user.email,
            username=user.username,
            is_admin=user.is_admin,
            is_suspended=user.is_suspended,
            created_at=user.created_at,
            download_count=count,
            bytes_stored=int(size),
        )
        for user, count, size in rows
    ]


@router.get("/downloads", response_model=list[AdminDownloadOut])
def recent_downloads(db: DbSession, _: AdminUser, limit: int = 50):
    rows = (
        db.query(Download, User.username)
        .join(User, User.id == Download.user_id)
        .order_by(Download.created_at.desc())
        .limit(min(limit, 200))
        .all()
    )
    return [
        AdminDownloadOut(
            id=dl.id,
            username=username,
            title=dl.title,
            filename=dl.filename,
            url=dl.url,
            status=dl.status,
            total_bytes=dl.total_bytes,
            created_at=dl.created_at,
        )
        for dl, username in rows
    ]


def _user_or_404(db: DbSession, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _admin_count(db: DbSession) -> int:
    return (
        db.query(func.count(User.id))
        .filter(User.is_admin.is_(True), User.is_suspended.is_(False))
        .scalar()
        or 0
    )


def _user_response(db: DbSession, user: User) -> AdminUserOut:
    count, size = (
        db.query(
            func.count(Download.id),
            func.coalesce(func.sum(Download.downloaded_bytes), 0),
        )
        .filter(Download.user_id == user.id)
        .one()
    )
    return AdminUserOut(
        id=user.id,
        email=user.email,
        username=user.username,
        is_admin=user.is_admin,
        is_suspended=user.is_suspended,
        created_at=user.created_at,
        download_count=count,
        bytes_stored=int(size),
    )


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(user_id: int, payload: AdminUserEdit, db: DbSession, admin: AdminUser):
    """Rename an account, change its address, or grant/revoke admin and access.

    The guards here are all about not locking everyone out: an admin editing
    their own row cannot suspend or demote themselves, and the last active
    admin cannot be stripped either way.
    """
    user = _user_or_404(db, user_id)
    changes = payload.model_dump(exclude_unset=True)
    # not a column — hashed separately below
    new_password = changes.pop("new_password", None)

    if user.id == admin.id:
        if changes.get("is_suspended"):
            raise HTTPException(status_code=400, detail="You cannot suspend your own account.")
        if changes.get("is_admin") is False:
            raise HTTPException(status_code=400, detail="You cannot remove your own admin access.")
        if new_password is not None:
            # Changing your own password on /auth/me requires the current one.
            # Allowing it here would route around that, so a stolen session
            # could lock the real owner out without ever knowing their password.
            raise HTTPException(
                status_code=400,
                detail="Change your own password from your Profile page.",
            )

    # Losing the last admin would leave the install unadministrable, and no
    # remaining account could undo it.
    loses_admin = user.is_admin and (
        changes.get("is_admin") is False or changes.get("is_suspended") is True
    )
    if loses_admin and _admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="This is the only admin — promote another first.")

    email = changes.get("email")
    if email and email != user.email:
        if db.query(User).filter(User.email == email, User.id != user.id).first():
            raise HTTPException(status_code=409, detail="Email already registered")

    for field, value in changes.items():
        setattr(user, field, value)
    if new_password is not None:
        user.hashed_password = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return _user_response(db, user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: DbSession, admin: AdminUser):
    """Remove an account, its downloads, and every file it owns.

    Irreversible, so the same lockout guards apply as for suspension.
    """
    user = _user_or_404(db, user_id)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")
    if user.is_admin and _admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="This is the only admin — promote another first.")

    # Rows cascade through the relationship, but the files on disk do not.
    for dl in db.query(Download).filter(Download.user_id == user.id).all():
        storage.delete_files(dl.file_path, dl.thumbnail_path, *dl.slide_paths)
    storage.delete_files(user.avatar_path)

    db.delete(user)
    db.commit()

    # Whatever is left is the now-empty per-user folder; leave anything that
    # unexpectedly survived rather than deleting a tree we did not account for.
    folder = storage.settings.media_dir / str(user_id)
    try:
        folder.rmdir()
    except OSError:
        pass


def _review_or_404(db: DbSession, review_id: int) -> Review:
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.put("/logo", status_code=status.HTTP_204_NO_CONTENT)
def upload_logo(file: Annotated[UploadFile, File()], admin: AdminUser):
    """Replace the site logo; it doubles as the favicon for everyone."""
    try:
        storage.save_logo(file)
    except storage.UploadTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/logo", status_code=status.HTTP_204_NO_CONTENT)
def remove_logo(admin: AdminUser):
    """Back to the default MediaBox wordmark and icon."""
    storage.delete_logo()


@router.get("/reviews", response_model=list[ReviewOut])
def list_reviews(db: DbSession, _: AdminUser):
    return (
        db.query(Review)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .all()
    )


@router.post("/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(payload: ReviewCreate, db: DbSession, _: AdminUser):
    review = Review(**payload.model_dump())
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.patch("/reviews/{review_id}", response_model=ReviewOut)
def update_review(review_id: int, payload: ReviewEdit, db: DbSession, _: AdminUser):
    review = _review_or_404(db, review_id)
    changes = payload.model_dump(exclude_unset=True)
    for required in ("author_name", "body"):
        if required in changes and changes[required] is None:
            raise HTTPException(status_code=422, detail=f"{required} cannot be blank")
    for field, value in changes.items():
        setattr(review, field, value)
    review.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    return review


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: int, db: DbSession, _: AdminUser):
    review = _review_or_404(db, review_id)
    db.delete(review)
    db.commit()
