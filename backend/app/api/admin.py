from fastapi import APIRouter
from sqlalchemy import func

from app.api.deps import AdminUser, DbSession
from app.models import Download, DownloadStatus, User
from app.schemas import AdminDownloadOut, AdminStats, AdminUserOut

router = APIRouter()


@router.get("/stats", response_model=AdminStats)
def stats(db: DbSession, _: AdminUser):
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
