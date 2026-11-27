import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import admin, public
from app.database import Base, get_db
from app.models import AppSetting, User
from app.security import create_access_token
from app.services import guest, guest_policy


class GuestSettingsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)
        self.admin = User(email="admin@example.com", username="admin", hashed_password="unused", is_admin=True)
        self.member = User(email="member@example.com", username="member", hashed_password="unused")
        self.delegated = User(email="delegate@example.com", username="delegate", hashed_password="unused", is_admin=True,
                              permissions={"plans.view": True, "plans.edit": True})
        self.db.add_all([self.admin, self.member, self.delegated])
        self.db.commit()
        self.headers = {"Authorization": f"Bearer {create_access_token(self.admin.id)}"}
        self.member_headers = {"Authorization": f"Bearer {create_access_token(self.member.id)}"}
        self.delegated_headers = {"Authorization": f"Bearer {create_access_token(self.delegated.id)}"}
        self.db.commit()

        app = FastAPI()
        app.include_router(admin.router, prefix="/admin")
        app.include_router(public.router, prefix="/public")
        app.dependency_overrides[get_db] = lambda: self.db
        self.policy_sessions = []
        def policy_session():
            session = Session(self.engine)
            self.policy_sessions.append(session)
            return session
        self.enterContext(patch.object(guest_policy, "SessionLocal", side_effect=policy_session))
        self.client = self.enterContext(TestClient(app))

    def save(self, qualities, default):
        return self.client.put("/admin/guest-settings", headers=self.headers,
                               json={"qualities": qualities, "default_quality": default})

    def test_existing_defaults_and_public_visibility(self):
        expected = {"qualities": ["720", "480"], "default_quality": "480"}
        self.assertEqual(self.client.get("/admin/guest-settings", headers=self.headers).json(), expected)
        public_settings = self.client.get("/public/limits").json()
        self.assertEqual({key: public_settings[key] for key in expected}, expected)

    def test_only_full_admin_can_manage_policy(self):
        for headers, expected in (({}, 401), (self.member_headers, 403), (self.delegated_headers, 403)):
            with self.subTest(headers=headers):
                self.assertEqual(self.client.get("/admin/guest-settings", headers=headers).status_code, expected)
                response = self.client.put("/admin/guest-settings", headers=headers,
                                           json={"qualities": ["480"], "default_quality": "480"})
                self.assertEqual(response.status_code, expected)

    def test_saved_policy_is_persistent_and_canonically_sorted(self):
        response = self.save(["480", "1080", "720", "1080"], "1080")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["qualities"], ["1080", "720", "480"])
        with Session(self.engine) as fresh:
            self.assertEqual(guest_policy.load(fresh).default_quality, "1080")
            self.assertIsNotNone(fresh.get(AppSetting, guest_policy.SETTING_KEY))
        self.assertEqual(self.client.get("/public/limits").json()["default_quality"], "1080")

    def test_invalid_policy_is_rejected_without_overwriting_previous_policy(self):
        self.save(["720"], "720")
        for qualities, default in (([], "480"), (["480"], "720"), (["9999"], "9999")):
            with self.subTest(qualities=qualities):
                self.assertEqual(self.save(qualities, default).status_code, 422)
        self.assertEqual(self.client.get("/public/limits").json()["qualities"], ["720"])

    def test_allowed_hd_and_default_reach_fetch_and_connection_is_released(self):
        self.save(["1080"], "1080")
        with tempfile.TemporaryDirectory() as parent:
            folder = Path(parent) / "guest"
            folder.mkdir()
            path = folder / "clip.mp4"
            path.write_bytes(b"media")
            def fetched(url, quality, *, policy):
                self.assertFalse(self.policy_sessions[-1].in_transaction())
                self.assertEqual(quality, "1080")
                self.assertEqual(policy.qualities, ["1080"])
                return path, folder

            with patch.object(guest, "fetch", side_effect=fetched) as fetch, patch.object(guest, "check_rate_limit"):
                response = self.client.post("/public/download", json={"url": "https://example.com/clip.mp4"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b"media")
            fetch.assert_called_once()
            self.assertFalse(folder.exists())

    def test_new_restrictions_reject_old_client_choice_before_quota_or_download(self):
        self.save(["480"], "480")
        with patch.object(guest, "fetch") as fetch, patch.object(guest, "check_rate_limit") as rate:
            response = self.client.post("/public/download", json={"url": "https://example.com/video", "quality": "720"})
        self.assertEqual(response.status_code, 400)
        rate.assert_not_called()
        fetch.assert_not_called()

    def test_best_quality_uses_empty_string_and_is_enforced_by_fetch(self):
        self.assertEqual(self.save([""], "").status_code, 200)
        policy = guest_policy.load(self.db)
        self.assertEqual(guest.normalise_quality(None, policy), "")
        self.assertEqual(self.client.get("/public/limits").json()["default_quality"], "")
        with tempfile.TemporaryDirectory() as parent:
            path = Path(parent) / "clip.mp4"
            path.write_bytes(b"media")
            with patch.object(guest, "is_ytdlp_url", return_value=True), \
                    patch.object(guest, "_fetch_ytdlp", return_value=path) as video:
                result, folder = guest.fetch("https://example.com/video", "", policy=policy)
            try:
                self.assertEqual(result, path)
                self.assertEqual(video.call_args.args[2], "")
            finally:
                guest.shutil.rmtree(folder)
