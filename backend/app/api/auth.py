from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import (
    MediaTokenOut,
    ProfileUpdate,
    TokenOut,
    UserCreate,
    UserLogin,
    UserOut,
)
from app.security import (
    MEDIA_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_media_token,
    hash_password,
    verify_password,
)

router = APIRouter()


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        # the very first account becomes the admin
        is_admin=db.query(User).count() == 0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update the current user's own profile (username, email, password)."""
    if payload.new_password is not None:
        if not payload.current_password or not verify_password(
            payload.current_password, user.hashed_password
        ):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        user.hashed_password = hash_password(payload.new_password)

    if payload.email is not None and payload.email != user.email:
        taken = (
            db.query(User)
            .filter(User.email == payload.email, User.id != user.id)
            .first()
        )
        if taken:
            raise HTTPException(status_code=409, detail="Email already registered")
        user.email = payload.email

    if payload.username is not None:
        user.username = payload.username

    db.commit()
    db.refresh(user)
    return user


@router.post("/media-token", response_model=MediaTokenOut)
def media_token(user: User = Depends(get_current_user)):
    """Short-lived URL-safe token for <img>/<a>/WebSocket usage."""
    return MediaTokenOut(
        token=create_media_token(user.id),
        expires_in=MEDIA_TOKEN_EXPIRE_MINUTES * 60,
    )
