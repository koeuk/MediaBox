from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Seeded for every user the first time they open their category list, so the
# tags that existed while categories were hardcoded keep their look.
DEFAULT_CATEGORIES: list[tuple[str, str]] = [
    ("Coding", "#6c8cff"),
    ("Fresh", "#3dca72"),
    ("Fun", "#f5a623"),
    ("View", "#e879f9"),
    ("Techs", "#22d3ee"),
    ("War", "#ef4444"),
    ("Top", "#eab308"),
    ("Car", "#f97316"),
    ("cuties", "#ec4899"),
    ("Memes", "#a78bfa"),
]


class Category(Base):
    """A user-defined download tag.

    Downloads reference their category by *name* (downloads.category), not by
    id — the column predates this table. Renames and deletes therefore have to
    cascade to the user's downloads by hand; see app/api/categories.py.
    """

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_category_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(50))
    # hex, "#rrggbb" — the UI tints pills and tabs from this
    color: Mapped[str] = mapped_column(String(7), default="#6c8cff")
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
