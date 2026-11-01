import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.admin import router as admin_router
from app.api.public import router as public_router
from app.config import settings
from app.models import User
from app.security import create_access_token
from app.services import storage


class BrandingTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.original_media_dir = settings.media_dir
        settings.media_dir = self.tmp_dir

        self.app = FastAPI()
        self.app.include_router(public_router, prefix="/public")
        self.app.include_router(admin_router, prefix="/admin")

        self.client = TestClient(self.app)

        from app.api.deps import get_admin_user

        self.admin = User(id=1, email="admin@example.com", username="admin", is_admin=True)

        async def mock_admin():
            return self.admin

        self.app.dependency_overrides[get_admin_user] = mock_admin
        self.headers = {"Authorization": "Bearer fake-token"}

    def tearDown(self):
        settings.media_dir = self.original_media_dir
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_default_title(self):
        res = self.client.get("/public/branding")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"site_title": "MediaBox", "has_logo": False})

    def test_update_and_reset_title(self):
        # Update title
        res = self.client.put(
            "/admin/branding/title",
            json={"site_title": "Awesome Stream"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"site_title": "Awesome Stream", "has_logo": False})

        # Check public branding returns new title
        res2 = self.client.get("/public/branding")
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["site_title"], "Awesome Stream")

        # Reset title
        res3 = self.client.delete("/admin/branding/title", headers=self.headers)
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(res3.json()["site_title"], "MediaBox")

        # Public branding reverts to default
        res4 = self.client.get("/public/branding")
        self.assertEqual(res4.status_code, 200)
        self.assertEqual(res4.json()["site_title"], "MediaBox")

    def test_empty_or_whitespace_title_rejected(self):
        res = self.client.put(
            "/admin/branding/title",
            json={"site_title": "   "},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 422)
