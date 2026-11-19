from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.models import Feedback
from app.schemas import FeedbackCreate, FeedbackOut

router = APIRouter()


@router.get("", response_model=list[FeedbackOut])
def list_feedback(
    db: DbSession,
    category: str | None = Query(default=None),
):
    query = db.query(Feedback).filter(Feedback.is_published.is_(True))
    if category and category.lower() != "all":
        query = query.filter(Feedback.category == category.lower())
    return query.order_by(Feedback.created_at.desc(), Feedback.id.desc()).all()


@router.post("", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    db: DbSession,
    user: OptionalUser,
):
    data = payload.model_dump()
    if user:
        data["user_id"] = user.id
        if not data.get("author_name"):
            data["author_name"] = user.username
        if not data.get("author_email"):
            data["author_email"] = user.email
    else:
        if not data.get("author_name"):
            data["author_name"] = "Anonymous"

    feedback = Feedback(**data)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("/me", response_model=list[FeedbackOut])
def my_feedback(db: DbSession, user: CurrentUser):
    return (
        db.query(Feedback)
        .filter(Feedback.user_id == user.id)
        .order_by(Feedback.created_at.desc(), Feedback.id.desc())
        .all()
    )
