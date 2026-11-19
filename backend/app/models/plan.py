from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Plan(Base):
    """A purchasable subscription length and what it costs.

    Rows are seeded once at startup with a zero price; the admin sets the real
    figures on the Admin page, so pricing is data rather than something baked
    into the code.
    """

    __tablename__ = "plans"

    # short stable key used by the API ("week", "month", …) — the label is what
    # people see, so it can be reworded without breaking stored references
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    label: Mapped[str] = mapped_column(String(40))
    days: Mapped[int] = mapped_column(Integer)
    # Numeric, not float: money that round-trips through binary fractions ends
    # up displaying as 2.9999999
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


# Seeded on first run. Prices start at 0 — the admin fills them in.
DEFAULT_PLANS = [
    ("week", "1 week", 7, 1),
    ("3weeks", "3 weeks", 21, 2),
    ("month", "1 month", 30, 3),
    ("year", "1 year", 365, 4),
]
