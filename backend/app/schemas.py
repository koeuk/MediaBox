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


class ProfileUpdate(BaseModel):
    """Fields a user may change on their own account. All optional; a password
    change additionally requires the correct current_password."""

    username: str | None = Field(default=None, min_length=2, max_length=80)
    email: EmailStr | None = None
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=6, max_length=128)


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
    category: str | None = None
    error: str | None
    is_favorite: bool
    has_thumbnail: bool
    can_retry: bool
    created_at: datetime
    completed_at: datetime | None


class DownloadCategoryUpdate(BaseModel):
    """Assigns (or clears) the tag on a single download."""

    category: str | None = Field(default=None, max_length=50)


HEX_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#6c8cff", pattern=HEX_COLOR_PATTERN)


class CategoryEdit(BaseModel):
    """All optional — omitted fields are left alone."""

    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, pattern=HEX_COLOR_PATTERN)
    position: int | None = Field(default=None, ge=0)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str
    position: int
    created_at: datetime
    # how many of the user's downloads currently carry this tag
    download_count: int = 0


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
