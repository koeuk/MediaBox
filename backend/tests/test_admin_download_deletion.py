import json
import tempfile
import threading
import sys
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import admin
from app.database import Base, get_db, run_migrations
from app.models import Download, DownloadStatus, User
from app.security import create_access_token
from app.services import admin_downloads, extractor, jobs, object_store, storage
from app.services.tasks import Cancelled, checkpoint, request_cancel, take_cancel


class AdminDownloadDeletionTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)
        self.admin = User(email="admin@example.com", username="admin", hashed_password="unused", is_admin=True)
        self.member = User(email="member@example.com", username="member", hashed_password="unused")
        self.viewer = User(email="viewer@example.com", username="viewer", hashed_password="unused", permissions={"downloads.view": True})
        self.db.add_all([self.admin, self.member, self.viewer])
        self.db.commit()
        self.headers = {"Authorization": f"Bearer {create_access_token(self.admin.id)}"}
        self.member_headers = {"Authorization": f"Bearer {create_access_token(self.member.id)}"}
        self.viewer_headers = {"Authorization": f"Bearer {create_access_token(self.viewer.id)}"}
        self.db.commit()
        app = FastAPI()
        app.include_router(admin.router, prefix="/admin")
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = self.enterContext(TestClient(app))

    def record(self, name, status=DownloadStatus.completed, user=None):
        path = self.folder / name
        path.write_bytes(b"media")
        dl = Download(user_id=(user or self.member).id, url="https://example.com/video", title=name,
                      file_path=str(path), status=status)
        self.db.add(dl)
        self.db.commit()
        return dl

    def delete(self, ids, headers=None):
        return self.client.post("/admin/downloads/delete", headers=headers or self.headers, json={"ids": ids})

    def test_bulk_deletes_cross_user_records_and_every_local_artifact(self):
        one = self.record("first.jpg")
        two = self.record("other.mp4", user=self.admin)
        slide = self.folder / "slide.jpg"
        thumbnail = self.folder / "thumb.jpg"
        slide.write_bytes(b"slide")
        thumbnail.write_bytes(b"thumb")
        one.slides = json.dumps([one.file_path, str(slide)])
        one.thumbnail_path = str(thumbnail)
        self.db.commit()
        ids = [one.id, two.id]
        response = self.delete(ids)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"deleted_ids": ids, "failed": []})
        self.assertEqual(self.db.query(Download).count(), 0)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_view_permission_and_own_media_delete_do_not_grant_admin_delete(self):
        dl = self.record("protected.mp4")
        for headers, expected in (({}, 401), (self.member_headers, 403), (self.viewer_headers, 403)):
            response = self.client.post("/admin/downloads/delete", headers=headers, json={"ids": [dl.id]})
            self.assertEqual(response.status_code, expected)
        self.assertIsNotNone(self.db.get(Download, dl.id))

    def test_delete_permission_can_be_delegated_but_requires_view(self):
        dl = self.record("delegated.mp4")
        self.viewer.permissions = {"downloads.view": True, "downloads.delete": True}
        self.db.commit()
        self.assertEqual(self.delete([dl.id], self.viewer_headers).json()["failed"], [])
        dl = self.record("still-protected.mp4")
        self.viewer.permissions = {"downloads.view": False, "downloads.delete": True}
        self.db.commit()
        self.assertEqual(self.delete([dl.id], self.viewer_headers).status_code, 403)

    def test_remote_artifacts_are_deleted_without_fetching_them(self):
        dl = self.record("remote.mp4")
        self.folder.joinpath("remote.mp4").unlink()
        from app.config import settings
        key = f"{settings.app_env}/media/{self.member.id}/file.mp4"
        dl.file_path = object_store.reference_for(key)
        self.db.commit()
        s3 = Mock()
        with patch.object(object_store, "get_spaces_client", return_value=s3):
            response = self.delete([dl.id])
        self.assertEqual(response.json()["failed"], [])
        s3.delete_object.assert_called_once_with(Bucket=settings.do_spaces_bucket, Key=key)
        s3.download_file.assert_not_called()

    def test_partial_failure_keeps_failed_record_for_retry(self):
        failed = self.record("failed.mp4")
        deleted = self.record("deleted.mp4")
        failed_id, deleted_id = failed.id, deleted.id
        original = storage.delete_files
        def remove(*paths):
            if paths[0].endswith("failed.mp4"):
                raise object_store.StorageError("sensitive storage information")
            original(*paths)
        with patch.object(storage, "delete_files", side_effect=remove):
            with self.assertLogs("app.services.admin_downloads", level="WARNING"):
                response = self.delete([failed_id, deleted_id])
        self.assertEqual(response.json()["deleted_ids"], [deleted_id])
        self.assertEqual(response.json()["failed"][0]["id"], failed_id)
        self.assertNotIn("sensitive", response.text)
        self.assertIsNotNone(self.db.get(Download, failed_id))
        self.assertIsNone(self.db.get(Download, deleted_id))
        self.assertTrue(self.folder.joinpath("failed.mp4").exists())

    def test_missing_records_files_and_duplicate_ids_are_idempotent(self):
        dl = self.record("missing.mp4")
        ident = dl.id
        self.folder.joinpath("missing.mp4").unlink()
        response = self.delete([ident, ident, 99999])
        self.assertEqual(response.json(), {"deleted_ids": [ident, 99999], "failed": []})

    def test_batch_validation(self):
        for ids in ([], [0], [-1], list(range(1, 202))):
            with self.subTest(ids=ids[:3]):
                self.assertEqual(self.delete(ids).status_code, 422)

    def test_active_worker_stops_before_files_are_removed(self):
        dl = self.record("active.mp4", DownloadStatus.downloading)
        ident = dl.id
        started = threading.Event()
        stopped = threading.Event()
        observed = []
        def worker():
            with jobs.download_lock(ident):
                started.set()
                while not stopped.wait(0.01):
                    try:
                        checkpoint(ident)
                    except Cancelled:
                        observed.append(self.folder.joinpath("active.mp4").exists())
                        stopped.set()
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        self.assertTrue(started.wait(1))
        try:
            response = self.delete([ident])
            self.assertEqual(response.json()["failed"], [])
            self.assertEqual(observed, [True])
            self.assertFalse(self.folder.joinpath("active.mp4").exists())
        finally:
            stopped.set()
            thread.join(1)

    def test_busy_worker_keeps_record_and_files_until_retry(self):
        dl = self.record("busy.mp4", DownloadStatus.downloading)
        ident = dl.id
        ready, finish = threading.Event(), threading.Event()
        def worker():
            with jobs.download_lock(ident):
                ready.set()
                finish.wait(5)
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        self.assertTrue(ready.wait(1))
        try:
            with patch.object(admin_downloads, "STOP_TIMEOUT_SECONDS", 0):
                response = self.delete([ident])
            self.assertEqual(response.json()["deleted_ids"], [])
            self.assertIn("stopping", response.json()["failed"][0]["detail"])
            self.assertIsNotNone(self.db.get(Download, ident))
            self.assertTrue(self.folder.joinpath("busy.mp4").exists())
            self.assertTrue(take_cancel(ident))
        finally:
            finish.set()
            thread.join(1)
        self.assertEqual(self.delete([ident]).json()["failed"], [])

    def test_job_runner_holds_the_same_record_lock(self):
        results = []
        def job(ident):
            def attempt():
                lock = jobs.download_lock(ident)
                acquired = lock.acquire(blocking=False)
                results.append(acquired)
                if acquired:
                    lock.release()
            thread = threading.Thread(target=attempt)
            thread.start()
            thread.join(1)
        fake_queue = Mock()
        fake_queue.get.side_effect = [(job, (123,), threading.Event(), "test-generation"), SystemExit]
        with patch.object(jobs, "_jobs", fake_queue), patch.object(jobs, "_matches_generation", return_value=True):
            with self.assertRaises(SystemExit):
                jobs._worker()
        self.assertEqual(results, [False])
        fake_queue.task_done.assert_called_once()

    def test_deleted_queued_invocation_cannot_run_against_reused_sqlite_id(self):
        dl = self.record("queued.mp4", DownloadStatus.queued)
        ident = dl.id
        generation = dl.job_token
        fake_queue, old_job, new_job = Mock(), Mock(), Mock()
        with patch.object(jobs, "_jobs", fake_queue), patch.object(jobs, "_started", True):
            jobs.submit(old_job, ident, "old-private-source", generation=generation)
            old_item = fake_queue.put.call_args.args[0]
            self.assertEqual(self.delete([ident]).json()["failed"], [])
            replacement = self.record("replacement.mp4", DownloadStatus.queued, user=self.admin)
            self.assertEqual(replacement.id, ident)
            jobs.submit(new_job, replacement.id, generation=replacement.job_token)
            new_item = fake_queue.put.call_args.args[0]
            fake_queue.get.side_effect = [old_item, new_item, SystemExit]
            with patch("app.database.SessionLocal", side_effect=lambda: Session(self.engine)):
                with self.assertRaises(SystemExit):
                    jobs._worker()
        old_job.assert_not_called()
        new_job.assert_called_once_with(ident)

    def test_delayed_submission_does_not_run_against_replacement_row(self):
        dl = self.record("old.mp4", DownloadStatus.queued)
        ident, generation = dl.id, dl.job_token
        self.assertEqual(self.delete([ident]).json()["failed"], [])
        replacement = self.record("new.mp4", DownloadStatus.queued, user=self.admin)
        self.assertEqual(replacement.id, ident)
        fake_queue, stale_job, current_job = Mock(), Mock(), Mock()
        with patch.object(jobs, "_jobs", fake_queue), patch.object(jobs, "_started", True):
            jobs.submit(stale_job, ident, "old-private-source", generation=generation)
            stale_item = fake_queue.put.call_args.args[0]
            jobs.submit(current_job, ident, generation=replacement.job_token)
            current_item = fake_queue.put.call_args.args[0]
            # Even a late discard of the old generation must leave the new job valid.
            jobs.discard_pending(ident, generation)
            self.assertFalse(current_item[2].is_set())
            # Check DB generation separately from the already-invalidated ticket.
            stale_item[2].clear()
            fake_queue.get.side_effect = [stale_item, current_item, SystemExit]
            with patch("app.database.SessionLocal", side_effect=lambda: Session(self.engine)):
                with self.assertRaises(SystemExit):
                    jobs._worker()
        stale_job.assert_not_called()
        current_job.assert_called_once_with(ident)

    def test_migration_adds_job_identity_without_changing_existing_records(self):
        from sqlalchemy import inspect, text
        dl = self.record("legacy.mp4", DownloadStatus.failed, user=self.admin)
        ident = dl.id
        with self.engine.begin() as conn:
            conn.execute(text("ALTER TABLE downloads DROP COLUMN job_token"))
            run_migrations(conn)
            run_migrations(conn)
            self.assertIn("job_token", {column["name"] for column in inspect(conn).get_columns("downloads")})
            self.assertEqual(conn.execute(text("SELECT title FROM downloads WHERE id=:id"), {"id": ident}).scalar(), "legacy.mp4")
        self.db.expire_all()
        from app.services import library
        legacy = self.db.get(Download, ident)
        self.assertIsNone(legacy.job_token)
        with patch.object(jobs, "submit") as submit:
            library.requeue(self.db, legacy)
        self.assertEqual(len(legacy.job_token), 32)
        self.assertEqual(submit.call_args.kwargs["generation"], legacy.job_token)

    def test_cancelled_ytdlp_removes_untracked_partial_files(self):
        dl = SimpleNamespace(id=456, user_id=1, url="https://example.com/video", quality="720")
        self.folder.joinpath("unrelated.mp4").write_bytes(b"keep")
        ytdlp = Mock()
        def build_options(record, template, hook, source, attempt):
            return {"outtmpl": template, "progress_hooks": [hook]}
        def youtube(options):
            def extract(*args, **kwargs):
                prefix = options["outtmpl"].split("%", 1)[0]
                for suffix in ("video.mp4.part", "video.mp4.ytdl", "video.f137.mp4"):
                    Path(prefix + suffix).write_bytes(b"partial")
                options["progress_hooks"][0]({"status": "downloading"})
            context = Mock()
            context.__enter__ = Mock(return_value=SimpleNamespace(extract_info=extract))
            context.__exit__ = Mock(return_value=False)
            return context
        ytdlp.YoutubeDL.side_effect = youtube
        request_cancel(dl.id)
        with patch.dict(sys.modules, {"yt_dlp": ytdlp}), \
                patch.object(extractor, "_build_opts", side_effect=build_options), \
                patch.object(extractor, "limit_video_quality"), \
                patch.object(storage, "user_dir", return_value=self.folder):
            with self.assertRaises(Cancelled):
                extractor.run_ytdlp(dl, Mock())
        self.assertEqual([path.name for path in self.folder.iterdir()], ["unrelated.mp4"])
