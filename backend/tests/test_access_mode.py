import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import admin, downloads, payments, public
from app.database import Base, get_db
from app.models import AppSetting, Download, DownloadStatus, PaymentRequest, Plan, User
from app.security import create_access_token
from app.services.library import LibraryError


class AccessModeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.admin = User(email="admin@example.com", username="admin", hashed_password="unused", is_admin=True)
        self.member = User(email="member@example.com", username="member", hashed_password="unused")
        self.db.add_all([self.admin, self.member, Plan(code="week", label="1 week", days=7, price=5)])
        self.db.commit()
        self.admin_headers = {"Authorization": f"Bearer {create_access_token(self.admin.id)}"}
        self.member_headers = {"Authorization": f"Bearer {create_access_token(self.member.id)}"}
        app = FastAPI()
        for router, prefix in ((admin.router, "/admin"), (public.router, "/public"),
                               (downloads.router, "/downloads"), (payments.router, "/payments")):
            app.include_router(router, prefix=prefix)

        def test_db():
            yield self.db

        @app.exception_handler(LibraryError)
        async def library_error(request: Request, exc: LibraryError):
            return JSONResponse(status_code=exc.status, content={"detail": str(exc)})

        app.dependency_overrides[get_db] = test_db
        self.client = TestClient(app)
        self.worker = patch("app.services.library.jobs.submit").start()

    def tearDown(self):
        patch.stopall()
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def set_mode(self, paid):
        response = self.client.patch("/admin/access-settings", json={"paid_mode": paid}, headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        return response

    def test_default_is_paid_and_free_setting_persists(self):
        self.assertEqual(self.client.get("/public/access-settings").json(), {"paid_mode": True})
        self.set_mode(False)
        with Session(self.engine) as other:
            self.assertEqual(other.get(AppSetting, "paid_mode").value, "0")
        self.assertEqual(self.client.get("/public/access-settings").json(), {"paid_mode": False})
        self.set_mode(True)
        self.assertEqual(self.client.get("/admin/access-settings", headers=self.admin_headers).json(), {"paid_mode": True})

    def test_only_admin_can_read_or_change_admin_settings(self):
        for headers, expected in (({}, 401), (self.member_headers, 403)):
            self.assertEqual(self.client.get("/admin/access-settings", headers=headers).status_code, expected)
            self.assertEqual(self.client.patch("/admin/access-settings", json={"paid_mode": False}, headers=headers).status_code, expected)
        self.assertIsNone(self.db.get(AppSetting, "paid_mode"))

    def test_invalid_mode_is_rejected(self):
        response = self.client.patch("/admin/access-settings", json={"paid_mode": "unknown"}, headers=self.admin_headers)
        self.assertEqual(response.status_code, 422)

    def test_mode_controls_single_and_batch_downloads(self):
        for paid in (True, False, True):
            self.set_mode(paid)
            for quality in (None, "1080", "2160"):
                for path, payload in (
                    ("/downloads", {"url": "https://example.com/video.mp4", "quality": quality}),
                    ("/downloads/batch", {"urls": ["https://example.com/video.mp4"], "quality": quality}),
                ):
                    with self.subTest(paid=paid, quality=quality, path=path):
                        response = self.client.post(path, json=payload, headers=self.member_headers)
                        self.assertEqual(response.status_code, 402 if paid else 201)

    def test_paid_mode_keeps_720p_available(self):
        response = self.client.post("/downloads", json={"url": "https://example.com/video.mp4", "quality": "720"}, headers=self.member_headers)
        self.assertEqual(response.status_code, 201)

    def test_admin_and_subscriber_keep_premium_access(self):
        self.member.premium_until = datetime.now(timezone.utc) + timedelta(days=7)
        self.db.commit()
        expiry = self.member.premium_until
        for headers in (self.admin_headers, self.member_headers):
            response = self.client.post("/downloads", json={"url": "https://example.com/video.mp4"}, headers=headers)
            self.assertEqual(response.status_code, 201)
        self.set_mode(False)
        self.set_mode(True)
        self.db.refresh(self.member)
        self.assertEqual(self.member.premium_until, expiry)
        self.assertEqual(float(self.db.get(Plan, "week").price), 5)

    def test_retry_respects_switch_back_to_paid(self):
        item = Download(user_id=self.member.id, url="https://example.com/video.mp4", quality="2160", status=DownloadStatus.failed)
        self.db.add(item)
        self.db.commit()
        response = self.client.post(f"/downloads/{item.id}/retry", headers=self.member_headers)
        self.assertEqual(response.status_code, 402)
        self.db.refresh(item)
        self.assertEqual(item.status, DownloadStatus.failed)
        self.set_mode(False)
        response = self.client.post(f"/downloads/{item.id}/retry", headers=self.member_headers)
        self.assertEqual(response.status_code, 200)

    def test_free_mode_rejects_unnecessary_payment(self):
        self.set_mode(False)
        response = self.client.post("/payments", json={"plan_code": "week", "method": "cash"}, headers=self.member_headers)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.db.query(PaymentRequest).count(), 0)
        self.db.refresh(self.member)
        self.assertIsNone(self.member.premium_until)


if __name__ == "__main__":
    unittest.main()
