from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import DownloadStatus


class AdminStats(BaseModel):
    users: int
    downloads: int
    reviews: int
    queued: int
    downloading: int
    completed: int
    failed: int
    favorites: int
    bytes_stored: int


class AdminUserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    is_admin: bool
    created_at: datetime
    download_count: int
    bytes_stored: int


class AdminDownloadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    title: str | None
    filename: str | None
    url: str
    status: DownloadStatus
    total_bytes: int
    created_at: datetime
