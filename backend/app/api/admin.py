from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func

from app.api.deps import AdminUser, DbSession
from app.models import Download, DownloadStatus, Review, User
from app.schemas import (
    AdminDownloadOut,
    AdminStats,
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


def _review_or_404(db: DbSession, review_id: int) -> Review:
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


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
