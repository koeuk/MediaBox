"""Private DigitalOcean Spaces uploads and temporary download links."""

import logging
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import require_permission
from app.config import settings
from app.models import User

router = APIRouter()
logger = logging.getLogger(__name__)


def get_spaces_client():
    key = settings.do_spaces_key.get_secret_value()
    secret = settings.do_spaces_secret.get_secret_value()
    if not key or not secret or not settings.do_spaces_bucket:
        raise HTTPException(status_code=503, detail="DigitalOcean Spaces is not configured")
    return boto3.client(
        "s3",
        region_name=settings.do_spaces_region,
        endpoint_url=str(settings.do_spaces_endpoint),
        aws_access_key_id=key,
        aws_secret_access_key=secret,
        config=Config(signature_version="s3v4"),
    )


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

    filename = Path((file.filename or "upload").replace("\\", "/")).name or "upload"
    key = f"uploads/{user.id}/{uuid4().hex}-{filename}"
    try:
        s3.upload_fileobj(
            file.file,
            settings.do_spaces_bucket,
            key,
            ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
        )
    except (BotoCoreError, ClientError):
        logger.exception("Spaces upload failed")
        raise HTTPException(status_code=502, detail="Unable to upload file to Spaces") from None
    return {"key": key}


@router.get("/url/{key:path}")
def get_url(
    key: str,
    user: Annotated[User, Depends(require_permission("media.view"))],
    s3=Depends(get_spaces_client),
):
    if not key.startswith(f"uploads/{user.id}/"):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.do_spaces_bucket, "Key": key},
            ExpiresIn=3600,
        )
    except (BotoCoreError, ClientError):
        logger.exception("Spaces URL signing failed")
        raise HTTPException(status_code=502, detail="Unable to generate download link") from None
    return {"url": url}
