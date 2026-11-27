"""Exercise the real library API and persistence with an in-memory S3 transport."""

import io
import json
import shutil
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError
from boto3.exceptions import S3UploadFailedError
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import downloads
from app.api.deps import get_current_user, get_media_user
from app.config import settings
from app.database import Base, get_db
from app.models import Download, DownloadStatus, User
from app.services import converter, downloader, library, object_store, storage


class MemorySpaces:
    def __init__(self):
        self.objects = {}
        self.content_types = {}

    def upload_file(self, filename, bucket, key, ExtraArgs):
        self.objects[key] = Path(filename).read_bytes()
        self.content_types[key] = ExtraArgs["ContentType"]

    def download_file(self, bucket, key, filename):
        Path(filename).write_bytes(self.objects[key])

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")

    def delete_object(self, Bucket, Key):
        self.objects.pop(Key, None)

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        return f"https://spaces.example/{Params['Key']}?signature=temporary"


class SpacesLibraryTests(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.object(settings, "media_dir", Path(folder)))
        self.enterContext(patch.object(settings, "storage_backend", "spaces"))
        self.enterContext(patch.object(settings, "app_env", "test"))
        self.s3 = MemorySpaces()
        self.enterContext(patch.object(object_store, "get_spaces_client", return_value=self.s3))
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        self.addCleanup(self.db.close)
        self.user = User(email="spaces@example.com", username="spaces", hashed_password="unused", is_admin=True)
        self.db.add(self.user)
        self.db.commit()
        self.app = FastAPI()
        self.app.include_router(downloads.router, prefix="/api/downloads")
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.app.dependency_overrides[get_media_user] = lambda: self.user

        @self.app.exception_handler(object_store.StorageError)
        @self.app.exception_handler(library.LibraryError)
        async def error_handler(request, exc):
            return JSONResponse(status_code=exc.status, content={"detail": str(exc)})

        self.client = self.enterContext(TestClient(self.app))

    def upload(self, name="clip.wav", data=b"audio"):
        with patch("app.services.ffmpeg.make_thumbnail", return_value=None):
            response = self.client.post("/api/downloads/upload", files={"file": (name, data, "audio/wav")})
        self.assertEqual(response.status_code, 201, response.text)
        return self.db.get(Download, response.json()["id"])

    def test_frontend_upload_survives_local_file_removal_and_deletes_remote(self):
        record = self.upload()
        self.assertTrue(record.file_path.startswith("s3://"))
        self.assertEqual(list(settings.media_dir.rglob("*.wav")), [])
        response = self.client.get(f"/api/downloads/{record.id}/file", follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertIn("test/media/", response.headers["location"])
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        with storage.local_file(record.file_path) as source:
            self.assertEqual(source.read_bytes(), b"audio")
        self.assertFalse(source.exists())
        self.assertEqual(self.client.delete(f"/api/downloads/{record.id}").status_code, 204)
        self.assertFalse(self.s3.objects)

    def test_thumbnails_and_slides_are_published_once(self):
        one = storage.new_path(self.user.id, "slide1.jpg")
        two = storage.new_path(self.user.id, "slide2.jpg")
        thumb = storage.new_path(self.user.id, "thumb.jpg")
        for path in (one, two, thumb):
            path.write_bytes(b"image")
        dl = Download(user_id=self.user.id, url="upload://slides", status=DownloadStatus.completed,
                      file_path=str(one), thumbnail_path=str(thumb), slides=json.dumps([str(one), str(two)]))
        storage.persist_media(self.db, dl)
        self.assertEqual(len(self.s3.objects), 3)
        self.assertEqual(dl.file_path, dl.slide_paths[0])
        for endpoint in ("thumbnail", "slide/1"):
            self.assertEqual(self.client.get(f"/api/downloads/{dl.id}/{endpoint}", follow_redirects=False).status_code, 307)
        self.client.delete(f"/api/downloads/{dl.id}")
        self.assertFalse(self.s3.objects)

    def test_existing_local_files_remain_readable(self):
        path = storage.new_path(self.user.id, "old.wav")
        path.write_bytes(b"old media")
        dl = Download(user_id=self.user.id, url="upload://old.wav", status=DownloadStatus.completed, file_path=str(path))
        self.db.add(dl)
        self.db.commit()
        response = self.client.get(f"/api/downloads/{dl.id}/file")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"old media")

    def test_failed_commit_keeps_local_files_and_cleans_remote(self):
        path = storage.new_path(self.user.id, "uncommitted.wav")
        path.write_bytes(b"keep me")
        dl = Download(user_id=self.user.id, url="upload://x", file_path=str(path))
        db = Mock()
        db.commit.side_effect = RuntimeError("database unavailable")
        with self.assertRaises(RuntimeError):
            storage.persist_media(db, dl)
        self.assertTrue(path.exists())
        self.assertFalse(self.s3.objects)
        db.rollback.assert_called_once()

    def test_failed_upload_does_not_create_completed_row(self):
        with patch.object(object_store, "upload_path", side_effect=object_store.StorageError()):
            with patch("app.services.ffmpeg.make_thumbnail", return_value=None):
                response = self.client.post("/api/downloads/upload", files={"file": ("x.wav", b"audio", "audio/wav")})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(self.db.query(Download).count(), 0)
        self.assertEqual(list(settings.media_dir.rglob("*.wav")), [])

    def test_content_type_is_retained_for_extensionless_media(self):
        record = self.upload(name="audio")
        self.assertEqual(self.s3.content_types[object_store.key_for(record.file_path)], "audio/wav")

    def test_retry_republishes_complete_staged_download_without_http(self):
        path = storage.new_path(self.user.id, "staged.wav")
        path.write_bytes(b"complete")
        dl = Download(user_id=self.user.id, url="https://example.com/staged.wav", filename="staged.wav",
                      file_path=str(path), status=DownloadStatus.failed, total_bytes=8, content_type="audio/wav")
        self.db.add(dl)
        self.db.commit()
        with patch.object(downloader, "SessionLocal", side_effect=lambda: Session(self.engine)), \
                patch.object(downloader.httpx, "Client") as http, \
                patch.object(downloader.ffmpeg, "make_thumbnail", return_value=None):
            downloader.run_download(dl.id, resume=True)
        http.assert_not_called()
        self.db.refresh(dl)
        self.assertEqual(dl.status, DownloadStatus.completed, dl.error)
        self.assertTrue(object_store.is_remote(dl.file_path))

    def test_migration_keeps_original_and_updates_derived_retry_source(self):
        path = storage.new_path(self.user.id, "old.wav")
        path.write_bytes(b"old media")
        source = Download(user_id=self.user.id, url="upload://old", status=DownloadStatus.completed, file_path=str(path))
        derived = Download(user_id=self.user.id, url="upload://old", status=DownloadStatus.failed,
                           convert_source=str(path), convert_target="mp3")
        self.db.add_all([source, derived])
        self.db.commit()
        storage.persist_media(self.db, source, keep_local=True)
        self.db.refresh(derived)
        self.assertEqual(derived.convert_source, source.file_path)
        self.assertTrue(object_store.is_remote(derived.convert_source))
        self.assertTrue(path.exists())
        self.assertTrue(derived.can_retry)

    def test_environment_isolation(self):
        record = self.upload()
        with patch.object(settings, "app_env", "production"):
            with self.assertRaises(object_store.StorageError):
                object_store.signed_url(record.file_path)

    def test_sdk_transfer_error_returns_safe_storage_error(self):
        with patch.object(self.s3, "upload_file", side_effect=S3UploadFailedError("internal details")):
            with patch("app.services.ffmpeg.make_thumbnail", return_value=None):
                response = self.client.post("/api/downloads/upload", files={"file": ("x.wav", b"audio", "audio/wav")})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("internal details", response.text)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is required")
    def test_conversion_reads_remote_source_and_publishes_result(self):
        data = io.BytesIO()
        with wave.open(data, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(8000)
            wav.writeframes(b"\0\0" * 800)
        source = self.upload(data=data.getvalue())
        with patch.object(library.jobs, "submit"):
            converted = library.queue_conversion(self.db, self.user, source, "wav")
        with patch.object(converter, "SessionLocal", side_effect=lambda: Session(self.engine)):
            converter.run_convert(converted.id, source.file_path, "wav")
        self.db.refresh(converted)
        self.assertEqual(converted.status, DownloadStatus.completed, converted.error)
        self.assertTrue(object_store.is_remote(converted.file_path))
        with storage.local_file(converted.file_path) as output:
            with wave.open(str(output)) as wav:
                self.assertGreater(wav.getnframes(), 0)
