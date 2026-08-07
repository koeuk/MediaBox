from fastapi import APIRouter

from app.api.deps import DbSession
from app.models import Review
from app.schemas import ReviewOut

router = APIRouter()


@router.get("", response_model=list[ReviewOut])
def list_reviews(db: DbSession):
    return (
        db.query(Review)
        .filter(Review.is_published.is_(True))
        .order_by(Review.created_at.desc(), Review.id.desc())
        .all()
    )
