from pydantic import BaseModel, HttpUrl


class GuestDownloadRequest(BaseModel):
    url: HttpUrl
    # validated against GUEST_QUALITIES in the service, so the allowed set
    # lives in one place
    quality: str | None = None


class GuestLimitsOut(BaseModel):
    qualities: list[str]
    default_quality: str
    max_size_mb: int
    rate_limit: int
    rate_window_seconds: int
