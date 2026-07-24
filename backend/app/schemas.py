from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from app.models import DownloadStatus


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    is_admin: bool
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MediaTokenOut(BaseModel):
    token: str
    expires_in: int  # seconds


QUALITY_PATTERN = r"^(2160|1440|1080|720|480)$"


class DownloadCreate(BaseModel):
    url: HttpUrl
    title: str | None = Field(default=None, max_length=255)
    # max height for extracted videos; None = best available
    quality: str | None = Field(default=None, pattern=QUALITY_PATTERN)


class DownloadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: str | None
    filename: str | None
    status: DownloadStatus
    progress: float
    total_bytes: int
    downloaded_bytes: int
    content_type: str | None
    quality: str | None
    error: str | None
    is_favorite: bool
    has_thumbnail: bool
    can_retry: bool
    created_at: datetime
    completed_at: datetime | None


class BatchDownloadCreate(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=50)
    quality: str | None = Field(default=None, pattern=QUALITY_PATTERN)


class ConvertRequest(BaseModel):
    target: str = Field(pattern=r"^(mp4|webm|gif|mp3|m4a|wav)$")


class AdminStats(BaseModel):
    users: int
    downloads: int
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
