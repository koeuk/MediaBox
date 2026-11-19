"""Email password reset links: hashed, expiring, single-use credentials."""
import hashlib
import logging
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
from app.security import hash_password

logger = logging.getLogger(__name__)
REQUEST_MESSAGE = "If an eligible account uses this email, a password reset link will be sent. Please check your inbox and spam folder."
INVALID_LINK = "This password reset link is invalid or has expired. Request a new link."


def configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_username and settings.smtp_password.get_secret_value() and settings.smtp_from_email)


def token_digest(token: str, user: User) -> str:
    # Changing either credential invalidates an outstanding reset link.
    return hashlib.sha256(f"{token}\0{user.email}\0{user.hashed_password}".encode()).hexdigest()


def deliver(email: str, link: str) -> None:
    message = EmailMessage()
    message['Subject'] = 'Reset your password'
    message['From'] = str(settings.smtp_from_email)
    message['To'] = email
    message.set_content(
        f"A password reset was requested for your {settings.app_name} account.\n\n"
        f"Choose a new password using this link:\n{link}\n\n"
        f"This link expires in {settings.password_reset_expire_minutes} minutes and can be used once.\n"
        "If you did not request this, you can ignore this email. Your password has not changed.\n"
    )
    try:
        context = ssl.create_default_context()
        if settings.smtp_use_ssl:
            connection = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10, context=context)
        else:
            connection = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
        with connection as smtp:
            if not settings.smtp_use_ssl:
                smtp.starttls(context=context)
            smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        # Avoid logging the recipient, reset link, credentials, or SMTP reply.
        logger.error('Password reset email delivery failed. Check SMTP configuration and connectivity.')


def request(db: Session, email: str, background: BackgroundTasks) -> None:
    if not configured():
        raise HTTPException(status_code=503, detail="Password reset email is not available right now. Please contact an administrator.")
    user = db.query(User).filter(User.email == email, User.is_suspended.is_(False)).first()
    if user is None:
        return
    now = datetime.now(timezone.utc)
    token = f"{user.id}.{secrets.token_urlsafe(32)}"
    digest = token_digest(token, user)
    changed = db.query(User).filter(
        User.id == user.id, User.email == user.email, User.hashed_password == user.hashed_password,
        User.is_suspended.is_(False),
        or_(User.password_reset_requested_at.is_(None), User.password_reset_requested_at <= now - timedelta(seconds=60)),
    ).update({
        User.password_reset_hash: digest,
        User.password_reset_expires_at: now + timedelta(minutes=settings.password_reset_expire_minutes),
        User.password_reset_requested_at: now,
    }, synchronize_session=False)
    db.commit()
    if changed:
        # Fragments never reach the web server or appear in HTTP referrers.
        link = f"{str(settings.frontend_url).rstrip('/')}/reset-password#token={token}"
        background.add_task(deliver, email, link)


def confirm(db: Session, token: str, new_password: str) -> None:
    try:
        selector, secret = token.split('.', 1)
        if not selector.isdecimal() or len(selector) > 19 or not 0 < int(selector) <= 2**63 - 1 or len(secret) != 43:
            raise ValueError
        user = db.get(User, int(selector))
    except (ValueError, OverflowError):
        raise HTTPException(status_code=400, detail=INVALID_LINK)
    if user is None or user.is_suspended:
        raise HTTPException(status_code=400, detail=INVALID_LINK)
    digest = token_digest(token, user)
    now = datetime.now(timezone.utc)
    if not user.password_reset_hash or not secrets.compare_digest(digest, user.password_reset_hash):
        raise HTTPException(status_code=400, detail=INVALID_LINK)
    expires = user.password_reset_expires_at
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires is None or expires <= now:
        raise HTTPException(status_code=400, detail=INVALID_LINK)
    changed = db.query(User).filter(
        User.id == user.id, User.password_reset_hash == digest,
        User.password_reset_expires_at > now, User.is_suspended.is_(False),
        User.email == user.email, User.hashed_password == user.hashed_password,
    ).update({
        User.hashed_password: hash_password(new_password),
        User.password_reset_hash: None,
        User.password_reset_expires_at: None,
        User.session_version: User.session_version + 1,
    }, synchronize_session=False)
    db.commit()
    if not changed:
        raise HTTPException(status_code=400, detail=INVALID_LINK)
