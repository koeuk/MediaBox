"""Payment claims: what a member submits, and what an admin does with it."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import (
    DEFAULT_SETTINGS,
    AppSetting,
    PaymentRequest,
    PaymentStatus,
    Plan,
    User,
)
from app.services import plans as plan_service


# Repeat submissions of the same plan inside this window are the same click.
DUPLICATE_WINDOW_SECONDS = 60


class PaymentError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


# ── settings ──────────────────────────────────────────────────────────


def seed_settings(db: Session) -> None:
    existing = {k for (k,) in db.query(AppSetting.key).all()}
    missing = [
        AppSetting(key=k, value=v) for k, v in DEFAULT_SETTINGS.items() if k not in existing
    ]
    if missing:
        db.add_all(missing)
        db.commit()


def get_flag(db: Session, key: str, default: bool = True) -> bool:
    row = db.get(AppSetting, key)
    return default if row is None else row.value == "1"


def set_flag(db: Session, key: str, value: bool) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value="1" if value else "0"))
    else:
        row.value = "1" if value else "0"
    db.commit()


# ── requests ──────────────────────────────────────────────────────────


def submit(db: Session, user: User, plan_code: str, method: str) -> PaymentRequest:
    """Record that `user` says they paid. Does not grant anything.

    The amount is read from the plan, never from the request: a client-supplied
    figure only invites claims like "I paid 100" against a plan that costs 10.
    """
    if method not in ("cash", "qr"):
        raise PaymentError(f"Unknown payment method: {method}")
    if method == "cash" and not get_flag(db, "cash_enabled"):
        raise PaymentError("Cash payment is not available right now.")
    plan = db.get(Plan, plan_code)
    if plan is None:
        raise PaymentError("Plan not found", status=404)
    amount = float(plan.price)
    if amount <= 0:
        raise PaymentError("That plan has no price set yet — ask the admin.")

    # A double-clicked button must not buy the plan twice. Anything identical
    # within the window is treated as the same click and returns the original.
    recent = (
        db.query(PaymentRequest)
        .filter(
            PaymentRequest.user_id == user.id,
            PaymentRequest.plan_code == plan_code,
            PaymentRequest.created_at
            >= datetime.now(timezone.utc) - timedelta(seconds=DUPLICATE_WINDOW_SECONDS),
        )
        .order_by(PaymentRequest.created_at.desc())
        .first()
    )
    if recent is not None:
        return recent

    request = PaymentRequest(
        user_id=user.id,
        plan_code=plan_code,
        method=method,
        amount=amount,
        # Applied on the spot: there is no verification step, so the record is
        # a receipt of what was granted rather than a request to grant it.
        status=PaymentStatus.approved,
        reviewed_at=datetime.now(timezone.utc),
    )
    db.add(request)
    plan_service.apply(db, user, plan)
    db.commit()
    db.refresh(request)
    return request


def _open_or_404(db: Session, request_id: int) -> PaymentRequest:
    request = db.get(PaymentRequest, request_id)
    if request is None:
        raise PaymentError("Payment request not found", status=404)
    if request.status != PaymentStatus.pending:
        raise PaymentError("That request has already been reviewed.", status=409)
    return request


def approve(db: Session, admin: User, request_id: int) -> PaymentRequest:
    """Accept the claim and put the member on the plan they paid for."""
    request = _open_or_404(db, request_id)
    plan = db.get(Plan, request.plan_code)
    if plan is None:
        raise PaymentError("The plan on this request no longer exists.", status=409)
    member = db.get(User, request.user_id)
    if member is None:
        raise PaymentError("That account no longer exists.", status=409)

    plan_service.apply(db, member, plan)
    request.status = PaymentStatus.approved
    request.reviewed_at = datetime.now(timezone.utc)
    request.reviewed_by = admin.id
    db.commit()
    db.refresh(request)
    return request


def reject(db: Session, admin: User, request_id: int, note: str | None = None) -> PaymentRequest:
    request = _open_or_404(db, request_id)
    request.status = PaymentStatus.rejected
    request.note = note
    request.reviewed_at = datetime.now(timezone.utc)
    request.reviewed_by = admin.id
    db.commit()
    db.refresh(request)
    return request
