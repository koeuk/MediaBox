from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


GuestQuality = Literal["", "2160", "1440", "1080", "720", "480"]
QUALITY_ORDER = ("", "2160", "1440", "1080", "720", "480")


class GuestQualitySettings(BaseModel):
    qualities: list[GuestQuality] = Field(default_factory=lambda: ["720", "480"], min_length=1)
    default_quality: GuestQuality = "480"

    @model_validator(mode="after")
    def validate_default(self):
        if self.default_quality not in self.qualities:
            raise ValueError("Default quality must be one of the allowed guest qualities")
        self.qualities = [quality for quality in QUALITY_ORDER if quality in self.qualities]
        return self


class GuestDownloadRequest(BaseModel):
    url: HttpUrl
    # Validated against the saved guest policy before any download starts.
    quality: str | None = None


class GuestLimitsOut(BaseModel):
    qualities: list[str]
    default_quality: str
    max_size_mb: int
    rate_limit: int
    rate_window_seconds: int
