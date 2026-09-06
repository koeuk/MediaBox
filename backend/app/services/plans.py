"""Subscription plans: seeding, pricing, and applying one to an account."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import DEFAULT_PLANS, Plan, User


def seed(db: Session) -> None:
    """Create the built-in plans once, priced at zero for the admin to fill in.

    Only inserts what is missing, so an admin's edited prices survive a
    restart and a newly added plan still appears.
    """
    existing = {code for (code,) in db.query(Plan.code).all()}
    missing = [p for p in DEFAULT_PLANS if p[0] not in existing]
    if not missing:
        return
    db.add_all(
        Plan(code=code, label=label, days=days, price=0, sort_order=order)
        for code, label, days, order in missing
    )
    db.commit()


def listing(db: Session) -> list[Plan]:
    return db.query(Plan).order_by(Plan.sort_order.asc()).all()


def apply(db: Session, user: User, plan: Plan) -> User:
    """Put `user` on `plan`, extending rather than replacing existing time.

    Someone who renews before their current subscription lapses keeps what
    they already paid for — the new period is added to the end of it. Only a
    lapsed (or never-set) expiry starts from today.
    """
    now = datetime.now(timezone.utc)
    current = user.premium_until
    if current is not None and current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    start = current if current is not None and current > now else now
    user.premium_until = start + timedelta(days=plan.days)
    db.commit()
    db.refresh(user)
    return user


def clear(db: Session, user: User) -> User:
    """End the subscription now — for refunds and corrections."""
    user.premium_until = None
    db.commit()
    db.refresh(user)
    return user
