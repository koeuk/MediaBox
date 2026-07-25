from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import DEFAULT_CATEGORIES, Category, Download, User
from app.schemas import CategoryCreate, CategoryEdit, CategoryOut

router = APIRouter()


def _seed_defaults(db: Session, user: User) -> None:
    """Give a user the built-in set the first time they look at their list.

    Without this, upgrading accounts would open an empty category page while
    their downloads still carry the old hardcoded tag names.
    """
    db.add_all(
        Category(user_id=user.id, name=name, color=color, position=i)
        for i, (name, color) in enumerate(DEFAULT_CATEGORIES)
    )
    db.commit()


def _counts(db: Session, user: User) -> dict[str, int]:
    rows = (
        db.query(Download.category, func.count(Download.id))
        .filter(Download.user_id == user.id, Download.category.isnot(None))
        .group_by(Download.category)
        .all()
    )
    return {name: count for name, count in rows}


def _to_out(cat: Category, counts: dict[str, int]) -> CategoryOut:
    return CategoryOut(
        id=cat.id,
        name=cat.name,
        color=cat.color,
        position=cat.position,
        created_at=cat.created_at,
        download_count=counts.get(cat.name, 0),
    )


def _owned(category_id: int, db: Session, user: User) -> Category:
    cat = db.get(Category, category_id)
    if cat is None or cat.user_id != user.id:
        raise HTTPException(status_code=404, detail="Category not found")
    return cat


def _ordered(db: Session, user: User) -> list[Category]:
    return (
        db.query(Category)
        .filter(Category.user_id == user.id)
        .order_by(Category.position.asc(), Category.id.asc())
        .all()
    )


@router.get("", response_model=list[CategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cats = _ordered(db, user)
    if not cats:
        _seed_defaults(db, user)
        cats = _ordered(db, user)
    counts = _counts(db, user)
    return [_to_out(c, counts) for c in cats]


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be blank")

    existing = (
        db.query(Category)
        .filter(Category.user_id == user.id, func.lower(Category.name) == name.lower())
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail=f'"{name}" already exists')

    last = (
        db.query(func.coalesce(func.max(Category.position), -1))
        .filter(Category.user_id == user.id)
        .scalar()
    )
    cat = Category(user_id=user.id, name=name, color=payload.color, position=last + 1)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return _to_out(cat, _counts(db, user))


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    payload: CategoryEdit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cat = _owned(category_id, db, user)

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Name cannot be blank")
        clash = (
            db.query(Category)
            .filter(
                Category.user_id == user.id,
                Category.id != cat.id,
                func.lower(Category.name) == name.lower(),
            )
            .first()
        )
        if clash:
            raise HTTPException(status_code=409, detail=f'"{name}" already exists')

        if name != cat.name:
            # downloads reference the tag by name, so carry them along
            db.query(Download).filter(
                Download.user_id == user.id, Download.category == cat.name
            ).update({Download.category: name}, synchronize_session=False)
            cat.name = name

    if payload.color is not None:
        cat.color = payload.color
    if payload.position is not None:
        cat.position = payload.position

    db.commit()
    db.refresh(cat)
    return _to_out(cat, _counts(db, user))


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cat = _owned(category_id, db, user)
    # untag rather than orphan — the downloads themselves are untouched
    db.query(Download).filter(
        Download.user_id == user.id, Download.category == cat.name
    ).update({Download.category: None}, synchronize_session=False)
    db.delete(cat)
    db.commit()


@router.put("/reorder", response_model=list[CategoryOut])
def reorder_categories(
    ids: list[int],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    owned = {c.id: c for c in _ordered(db, user)}
    unknown = [i for i in ids if i not in owned]
    if unknown:
        raise HTTPException(status_code=404, detail=f"Unknown category ids: {unknown}")

    for position, cid in enumerate(ids):
        owned[cid].position = position
    db.commit()

    counts = _counts(db, user)
    return [_to_out(c, counts) for c in _ordered(db, user)]
