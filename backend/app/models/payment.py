from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PaymentStatus:
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class PaymentRequest(Base):
    """A member's claim that they have paid, waiting on an admin.

    Deliberately a claim and not a payment: nothing here proves money moved,
    so approving one is a human decision. The row exists so that decision has
    somewhere to happen instead of a message the admin has to remember.
    """

    __tablename__ = "payment_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_code: Mapped[str] = mapped_column(String(16))
    method: Mapped[str] = mapped_column(String(8))  # "cash" | "qr"
    amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[str] = mapped_column(String(8), default=PaymentStatus.pending, index=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user = relationship("User")


class AppSetting(Base):
    """Small key/value store for switches an admin flips at runtime."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[str] = mapped_column(String(255))


# key -> default, seeded on first run
DEFAULT_SETTINGS = {
    # whether the cash option appears in the upgrade dialog at all
    "cash_enabled": "1",
}
