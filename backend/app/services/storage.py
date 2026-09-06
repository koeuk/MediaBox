"""Filesystem layout for stored media: per-user folders, collision-free
destination paths, saving uploads, and deleting a record's files.
"""

import mimetypes
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

_UPLOAD_CHUNK = 1024 * 1024
# a profile picture has no business being larger than this
AVATAR_MAX_BYTES = 5 * 1024 * 1024


class UploadTooLarge(Exception):
    """Raised when an upload exceeds the configured size limit."""


def max_bytes() -> int:
    return settings.max_download_size_mb * 1024 * 1024


def user_dir(user_id: int) -> Path:
    """The user's media folder, created if missing."""
    path = settings.media_dir / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def new_path(user_id: int, filename: str) -> Path:
    """A collision-free destination inside the user's folder.

    The name is `<8 hex>_<filename>`; strip the prefix with
    `path.name.split("_", 1)[-1]` to recover the original filename.
    """
    return user_dir(user_id) / f"{uuid.uuid4().hex[:8]}_{Path(filename).name}"


def delete_files(*paths: str | None) -> None:
    for path in paths:
        if path:
            Path(path).unlink(missing_ok=True)


def save_avatar(file: UploadFile, user_id: int) -> Path:
    """Stream a profile picture to disk, in the user's own folder.

    Kept apart from `save_upload` on purpose: an avatar is not library media,
    so it must not land in the downloads list, and a few MB is plenty — the
    library's size limit would let someone store a 2 GB "picture".

    Raises ValueError for a non-image, UploadTooLarge past AVATAR_MAX_BYTES.
    """
    filename = Path(file.filename or "avatar").name
    content_type = (file.content_type or "").split(";")[0].strip()
    if not content_type or content_type == "application/octet-stream":
        content_type = mimetypes.guess_type(filename)[0] or ""
    if not content_type.startswith("image/"):
        raise ValueError("An avatar must be an image")

    suffix = Path(filename).suffix or mimetypes.guess_extension(content_type) or ".png"
    dest = user_dir(user_id) / f"avatar_{uuid.uuid4().hex[:8]}{suffix}"
    size = 0
    try:
        with open(dest, "wb") as fh:
            while chunk := file.file.read(_UPLOAD_CHUNK):
                size += len(chunk)
                if size > AVATAR_MAX_BYTES:
                    raise UploadTooLarge(
                        f"Image exceeds the {AVATAR_MAX_BYTES // (1024 * 1024)} MB limit"
                    )
                fh.write(chunk)
    except UploadTooLarge:
        dest.unlink(missing_ok=True)
        raise
    return dest


def _branding_dir() -> Path:
    path = settings.media_dir / "branding"
    path.mkdir(parents=True, exist_ok=True)
    return path


def find_logo() -> Path | None:
    """The uploaded site logo, or None when the default branding is in use."""
    return next(iter(_branding_dir().glob("logo.*")), None)


def save_logo(file: UploadFile) -> Path:
    """Replace the site logo (served as both navbar logo and favicon).

    Same rules as an avatar: images only, AVATAR_MAX_BYTES cap. The file is
    written under a temp name first so a failed upload leaves the old logo.
    """
    filename = Path(file.filename or "logo").name
    content_type = (file.content_type or "").split(";")[0].strip()
    if not content_type or content_type == "application/octet-stream":
        content_type = mimetypes.guess_type(filename)[0] or ""
    if not content_type.startswith("image/"):
        raise ValueError("The logo must be an image")

    suffix = Path(filename).suffix or mimetypes.guess_extension(content_type) or ".png"
    dest = _branding_dir() / f"logo{suffix}"
    tmp = dest.with_name(f"logo_tmp_{uuid.uuid4().hex[:8]}{suffix}")
    size = 0
    try:
        with open(tmp, "wb") as fh:
            while chunk := file.file.read(_UPLOAD_CHUNK):
                size += len(chunk)
                if size > AVATAR_MAX_BYTES:
                    raise UploadTooLarge(
                        f"Image exceeds the {AVATAR_MAX_BYTES // (1024 * 1024)} MB limit"
                    )
                fh.write(chunk)
    except UploadTooLarge:
        tmp.unlink(missing_ok=True)
        raise
    delete_logo()  # the old logo may have a different extension
    tmp.rename(dest)
    return dest


def delete_logo() -> None:
    for p in _branding_dir().glob("logo.*"):
        p.unlink(missing_ok=True)


def save_upload(file: UploadFile, user_id: int) -> tuple[Path, int, str]:
    """Stream an uploaded media file to disk.

    Returns (path, size, content_type). Raises ValueError for a non-media
    type and UploadTooLarge past the size limit.
    """
    filename = Path(file.filename or "upload").name
    content_type = (file.content_type or "").split(";")[0].strip()
    if not content_type or content_type == "application/octet-stream":
        content_type = mimetypes.guess_type(filename)[0] or ""
    if not content_type.startswith(("video/", "audio/", "image/")):
        raise ValueError("Only video, audio, or image files can be uploaded")

    dest = new_path(user_id, filename)
    limit = max_bytes()
    size = 0
    try:
        with open(dest, "wb") as fh:
            while chunk := file.file.read(_UPLOAD_CHUNK):
                size += len(chunk)
                if size > limit:
                    raise UploadTooLarge(
                        f"File exceeds the {settings.max_download_size_mb} MB limit"
                    )
                fh.write(chunk)
    except UploadTooLarge:
        dest.unlink(missing_ok=True)
        raise
    return dest, size, content_type
