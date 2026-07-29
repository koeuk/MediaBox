from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession, MediaUser
from app.models import User
from app.services import storage
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
def register(payload: UserCreate, db: DbSession):
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
def login(payload: UserLogin, db: DbSession):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(payload: ProfileUpdate, db: DbSession, user: CurrentUser):
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


@router.put("/me/avatar", response_model=UserOut)
def upload_avatar(file: Annotated[UploadFile, File()], db: DbSession, user: CurrentUser):
    """Replace the current user's profile picture."""
    try:
        dest = storage.save_avatar(file, user.id)
    except storage.UploadTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # only after the new one is safely on disk, so a failed write leaves the
    # old picture intact rather than the account with none at all
    previous = user.avatar_path
    user.avatar_path = str(dest)
    db.commit()
    db.refresh(user)
    storage.delete_files(previous)
    return user


@router.delete("/me/avatar", response_model=UserOut)
def delete_avatar(db: DbSession, user: CurrentUser):
    previous = user.avatar_path
    user.avatar_path = None
    db.commit()
    db.refresh(user)
    storage.delete_files(previous)
    return user


@router.get("/me/avatar")
def get_avatar(user: MediaUser):
    """The picture itself. MediaUser so an <img> can pass ?token= instead of a
    header, the same way thumbnails work."""
    if not user.avatar_path or not Path(user.avatar_path).exists():
        raise HTTPException(status_code=404, detail="No avatar set")
    return FileResponse(user.avatar_path)


@router.post("/media-token", response_model=MediaTokenOut)
def media_token(user: CurrentUser):
    """Short-lived URL-safe token for <img>/<a>/WebSocket usage."""
    return MediaTokenOut(
        token=create_media_token(user.id),
        expires_in=MEDIA_TOKEN_EXPIRE_MINUTES * 60,
    )
