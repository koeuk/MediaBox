from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


MEDIA_TOKEN_EXPIRE_MINUTES = 10


def create_access_token(user_id: int) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_media_token(user_id: int) -> str:
    """Short-lived token safe to embed in URLs (<img>, <a>, WebSocket).

    Scoped so it cannot be used against the regular API, and expiring fast
    enough that a leak via server logs or browser history is low-value.
    """
    expires = datetime.now(timezone.utc) + timedelta(minutes=MEDIA_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "scope": "media", "exp": expires}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
