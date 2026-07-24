"""Filesystem layout for stored media: per-user folders, collision-free
destination paths, saving uploads, and deleting a record's files.
"""

import mimetypes
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

_UPLOAD_CHUNK = 1024 * 1024


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
