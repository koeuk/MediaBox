from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_token

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
)


def _resolve_user(token: str | None, db: Session, allow_query_scope: bool) -> User:
    if not token:
        raise _credentials_error
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except Exception:
        raise _credentials_error
    if payload.get("scope") == "media" and not allow_query_scope:
        raise _credentials_error
    user = db.get(User, user_id)
    if user is None:
        raise _credentials_error
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Resolve the user from a Bearer access token (media tokens rejected)."""
    auth = request.headers.get("authorization", "")
    token = auth.split(" ", 1)[1] if auth.lower().startswith("bearer ") else None
    return _resolve_user(token, db, allow_query_scope=False)


def get_media_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Auth for file/thumbnail endpoints.

    Accepts the normal Bearer header, or a short-lived media-scoped token via
    `?token=` for <img>/<a> tags where headers cannot be attached. Long-lived
    access tokens are rejected in the query form so they never end up in
    server logs or browser history.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return _resolve_user(auth.split(" ", 1)[1], db, allow_query_scope=False)

    token = request.query_params.get("token")
    if not token:
        raise _credentials_error
    try:
        scope = decode_token(token).get("scope")
    except Exception:
        raise _credentials_error
    if scope != "media":
        raise _credentials_error
    return _resolve_user(token, db, allow_query_scope=True)
