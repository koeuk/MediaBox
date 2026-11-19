"""Member-facing payment claims."""

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, DbSession
from app.schemas import PaymentRequestOut, PaymentSubmit
from app.services import payments

router = APIRouter()


def _out(request, username: str, plan_label: str) -> PaymentRequestOut:
    return PaymentRequestOut(
        id=request.id,
        user_id=request.user_id,
        username=username,
        plan_code=request.plan_code,
        plan_label=plan_label,
        method=request.method,
        amount=float(request.amount),
        status=request.status,
        created_at=request.created_at,
    )


@router.post("", response_model=PaymentRequestOut, status_code=201)
def submit_payment(payload: PaymentSubmit, db: DbSession, user: CurrentUser):
    """Tell the admin you have paid. Grants nothing on its own."""
    try:
        request = payments.submit(db, user, payload.plan_code, payload.method)
    except payments.PaymentError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc))

    from app.models import Plan

    plan = db.get(Plan, request.plan_code)
    return _out(request, user.username, plan.label if plan else request.plan_code)


@router.get("/mine", response_model=list[PaymentRequestOut])
def my_payments(db: DbSession, user: CurrentUser):
    """So the dialog can say "already waiting" instead of offering to re-send."""
    from app.models import PaymentRequest, Plan

    rows = (
        db.query(PaymentRequest, Plan.label)
        .outerjoin(Plan, Plan.code == PaymentRequest.plan_code)
        .filter(PaymentRequest.user_id == user.id)
        .order_by(PaymentRequest.created_at.desc())
        .limit(10)
        .all()
    )
    return [_out(r, user.username, label or r.plan_code) for r, label in rows]
