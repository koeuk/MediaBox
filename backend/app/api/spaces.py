"""Private DigitalOcean Spaces uploads and temporary download links."""

import logging
from typing import Annotated

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import require_permission
from app.config import settings
from app.models import User
from app.services.object_store import get_spaces_client, new_key

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload")
def upload(
    user: Annotated[User, Depends(require_permission("media.create"))],
    file: Annotated[UploadFile, File()],
    s3=Depends(get_spaces_client),
):
    # Check the spooled file before starting any remote upload.
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > settings.max_download_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds the configured upload limit")

    key = new_key(user.id, file.filename or "upload", kind="uploads")
    try:
        s3.upload_fileobj(
            file.file,
            settings.do_spaces_bucket,
            key,
            ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
        )
    except (BotoCoreError, ClientError):
        logger.warning("Spaces upload failed")
        raise HTTPException(status_code=502, detail="Unable to upload file to Spaces") from None
    return {"key": key}


@router.get("/url/{key:path}")
def get_url(
    key: str,
    user: Annotated[User, Depends(require_permission("media.view"))],
    s3=Depends(get_spaces_client),
):
    if not key.startswith(f"{settings.app_env}/uploads/{user.id}/"):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.do_spaces_bucket, "Key": key},
            ExpiresIn=3600,
        )
    except (BotoCoreError, ClientError):
        logger.warning("Spaces URL signing failed")
        raise HTTPException(status_code=502, detail="Unable to generate download link") from None
    return {"url": url}
