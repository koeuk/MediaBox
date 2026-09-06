from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

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
    is_suspended: bool
    created_at: datetime
    download_count: int
    bytes_stored: int


class AdminUserEdit(BaseModel):
    """Every field optional — the admin form sends only what it changed."""

    username: str | None = Field(default=None, min_length=2, max_length=80)
    email: EmailStr | None = None
    is_admin: bool | None = None
    is_suspended: bool | None = None
    # an admin reset: no current password, because the whole point is that the
    # account holder cannot supply one
    new_password: str | None = Field(default=None, min_length=6, max_length=128)


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
