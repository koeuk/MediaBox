from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models import DownloadStatus

# max video height accepted for yt-dlp extraction; anything else is rejected
QUALITY_PATTERN = r"^(2160|1440|1080|720|480)$"
CONVERT_TARGET_PATTERN = r"^(mp4|webm|gif|mp3|m4a|wav)$"
# see services.bgremove.QUALITY_MODELS for what each tier maps to
CUTOUT_QUALITY_PATTERN = r"^(fast|good|best)$"


class DownloadCreate(BaseModel):
    url: HttpUrl
    title: str | None = Field(default=None, max_length=255)
    # max height for extracted videos; None = best available
    quality: str | None = Field(default=None, pattern=QUALITY_PATTERN)


class BatchDownloadCreate(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=50)
    quality: str | None = Field(default=None, pattern=QUALITY_PATTERN)


class DownloadCategoryUpdate(BaseModel):
    """Assigns (or clears) the tag on a single download."""

    category: str | None = Field(default=None, max_length=50)


class ConvertRequest(BaseModel):
    target: str = Field(pattern=CONVERT_TARGET_PATTERN)


class RemoveBackgroundRequest(BaseModel):
    quality: str = Field(default="good", pattern=CUTOUT_QUALITY_PATTERN)


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
    # "cutout" for background removal; null for downloads and conversions
    job_kind: str | None = None
    error: str | None
    is_favorite: bool
    is_hidden: bool = False
    has_thumbnail: bool
    can_retry: bool
    created_at: datetime
    completed_at: datetime | None
