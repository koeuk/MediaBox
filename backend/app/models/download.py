import enum
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DownloadStatus(str, enum.Enum):
    queued = "queued"
    downloading = "downloading"
    completed = "completed"
    failed = "failed"


class Download(Base):
    __tablename__ = "downloads"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[DownloadStatus] = mapped_column(
        Enum(DownloadStatus), default=DownloadStatus.queued, index=True
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    total_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    downloaded_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # max video height for yt-dlp downloads ("720", "1080", …); None = best
    quality: Mapped[str | None] = mapped_column(String(8), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None, index=True)
    # set on records derived from another file (convert, cutout) so retry
    # re-runs the right worker instead of trying to fetch the URL again
    convert_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    convert_target: Mapped[str | None] = mapped_column(String(8), nullable=True)
    # "cutout" for background removal; NULL means download-or-convert, which is
    # what every row created before this column existed is
    job_kind: Mapped[str | None] = mapped_column(String(16), nullable=True, default=None)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    # kept out of the default views without being deleted
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    owner = relationship("User", back_populates="downloads")

    @property
    def has_thumbnail(self) -> bool:
        return self.thumbnail_path is not None

    @property
    def is_derived(self) -> bool:
        """True when this row was produced from another file on disk rather
        than fetched from its URL — a conversion or a cutout."""
        return bool(self.convert_source)

    @property
    def can_retry(self) -> bool:
        """Whether /retry can actually do something for this record."""
        if self.status != DownloadStatus.failed:
            return False
        if self.is_derived:
            return Path(self.convert_source).exists()
        return self.url.lower().startswith(("http://", "https://"))
