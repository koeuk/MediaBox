"""Private, environment-scoped Spaces objects. Never store signed URLs in the DB."""

import mimetypes
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote
from uuid import uuid4

import boto3
from boto3.exceptions import S3UploadFailedError
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings


class StorageError(Exception):
    def __init__(self, message="Object storage is unavailable", status=502):
        super().__init__(message)
        self.status = status


def get_spaces_client():
    key = settings.do_spaces_key.get_secret_value()
    secret = settings.do_spaces_secret.get_secret_value()
    if not key or not secret or not settings.do_spaces_bucket:
        raise StorageError("DigitalOcean Spaces is not configured", status=503)
    return boto3.client(
        "s3", region_name=settings.do_spaces_region,
        endpoint_url=str(settings.do_spaces_endpoint),
        aws_access_key_id=key, aws_secret_access_key=secret,
        config=Config(
            signature_version="s3v4", connect_timeout=10, read_timeout=120,
            retries={"mode": "standard", "max_attempts": 3},
            # Spaces does not implement all newer AWS checksum extensions.
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


def new_key(user_id: int, filename: str, kind: str = "media") -> str:
    name = Path(filename.replace("\\", "/")).name or "file"
    # Bound UTF-8 names as well as ASCII names so object keys stay short.
    name = name.encode("utf-8")[:200].decode("utf-8", errors="ignore")
    return f"{settings.app_env}/{kind}/{user_id}/{uuid4().hex}-{name}"


def is_remote(reference: str | None) -> bool:
    return bool(reference and reference.startswith("s3://"))


def reference_for(key: str) -> str:
    return f"s3://{settings.do_spaces_bucket}/{key}"


def key_for(reference: str) -> str:
    prefix = f"s3://{settings.do_spaces_bucket}/"
    if not reference.startswith(prefix):
        raise StorageError("Object belongs to a different bucket", status=404)
    key = reference[len(prefix):]
    if not key.startswith(f"{settings.app_env}/"):
        raise StorageError("Object belongs to a different environment", status=404)
    return key


def upload_path(path: Path, user_id: int, content_type: str | None = None) -> str:
    key = new_key(user_id, path.name)
    try:
        get_spaces_client().upload_file(
            str(path), settings.do_spaces_bucket, key,
            ExtraArgs={"ContentType": content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"},
        )
    except (BotoCoreError, ClientError, S3UploadFailedError) as exc:
        raise StorageError("Unable to upload file to Spaces") from exc
    return reference_for(key)


def delete(reference: str) -> None:
    key = key_for(reference)
    try:
        get_spaces_client().delete_object(Bucket=settings.do_spaces_bucket, Key=key)
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("Unable to delete file from Spaces") from exc


def exists(reference: str) -> bool:
    key = key_for(reference)
    try:
        get_spaces_client().head_object(Bucket=settings.do_spaces_bucket, Key=key)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return False
        raise StorageError() from exc
    except BotoCoreError as exc:
        raise StorageError() from exc
    return True


def signed_url(reference: str, filename: str | None = None) -> str:
    params = {"Bucket": settings.do_spaces_bucket, "Key": key_for(reference)}
    if filename:
        params["ResponseContentDisposition"] = f"attachment; filename*=UTF-8''{quote(filename, safe='')}"
    try:
        return get_spaces_client().generate_presigned_url("get_object", Params=params, ExpiresIn=3600)
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("Unable to generate download link") from exc


@contextmanager
def local_file(reference: str):
    """Fetch remote input just for the duration of a conversion or export."""
    if not is_remote(reference):
        path = Path(reference)
        if not path.is_file():
            raise FileNotFoundError("Source file is missing")
        yield path
        return
    key = key_for(reference)
    with TemporaryDirectory(prefix="mediabox-source-") as folder:
        path = Path(folder) / Path(key).name
        try:
            get_spaces_client().download_file(settings.do_spaces_bucket, key, str(path))
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Unable to retrieve source from Spaces") from exc
        yield path
