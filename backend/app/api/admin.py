from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Download, DownloadStatus, User
from app.schemas import AdminDownloadOut, AdminStats, AdminUserOut

router = APIRouter()


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


@router.get("/stats", response_model=AdminStats)
def stats(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    by_status = dict(
        db.query(Download.status, func.count(Download.id)).group_by(Download.status).all()
    )
    return AdminStats(
        users=db.query(func.count(User.id)).scalar() or 0,
        downloads=db.query(func.count(Download.id)).scalar() or 0,
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
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
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
def recent_downloads(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
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
