from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import MediaTokenOut, TokenOut, UserCreate, UserLogin, UserOut
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


@router.post("/media-token", response_model=MediaTokenOut)
def media_token(user: User = Depends(get_current_user)):
    """Short-lived URL-safe token for <img>/<a>/WebSocket usage."""
    return MediaTokenOut(
        token=create_media_token(user.id),
        expires_in=MEDIA_TOKEN_EXPIRE_MINUTES * 60,
    )
