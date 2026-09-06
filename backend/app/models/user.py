from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(80))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    # a suspended account keeps its data but cannot log in or use the API
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Paid tier: when the subscription runs out, not whether it exists. An
    # admin sets this after payment lands; there is no automated billing.
    # NULL means the account has never been on a plan.
    premium_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # absolute path to the profile picture; NULL means the initials fallback
    avatar_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    downloads = relationship(
        "Download", back_populates="owner", cascade="all, delete-orphan"
    )
    # Categories are per-user too, and their foreign key is ON DELETE NO ACTION,
    # so without this cascade the database refuses to delete any account that
    # has ever opened the categories page.
    categories = relationship("Category", cascade="all, delete-orphan")
    payments = relationship("PaymentRequest", cascade="all, delete-orphan")

    @property
    def has_avatar(self) -> bool:
        return self.avatar_path is not None

    @property
    def is_premium(self) -> bool:
        """Derived, never stored: a lapsed subscription must switch itself off
        without anyone having to run a job to flip a flag."""
        if self.premium_until is None:
            return False
        expiry = self.premium_until
        # SQLite hands back naive datetimes; compare like with like
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return expiry > datetime.now(timezone.utc)
