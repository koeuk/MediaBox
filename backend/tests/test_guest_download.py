import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import public
from app.services import guest


class GuestDownloadTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(public.router, prefix="/public")
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_download_without_token_streams_file_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as parent:
            folder = Path(parent) / "guest-download"
            folder.mkdir()
            path = folder / "clip.mp4"
            path.write_bytes(b"test-video")
            with patch.object(guest, "fetch", return_value=(path, folder)) as fetch, \
                    patch.object(guest, "check_rate_limit"):
                response = self.client.post("/public/download", json={
                    "url": "https://example.com/clip.mp4", "quality": "720",
                })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b"test-video")
            self.assertIn("clip.mp4", response.headers["content-disposition"])
            fetch.assert_called_once_with("https://example.com/clip.mp4", "720")
            self.assertFalse(folder.exists())

    def test_premium_quality_is_rejected_before_fetch_or_rate_limit(self):
        with patch.object(guest, "fetch") as fetch, \
                patch.object(guest, "check_rate_limit") as limit:
            response = self.client.post("/public/download", json={
                "url": "https://example.com/clip.mp4", "quality": "1080",
            })
        self.assertEqual(response.status_code, 400)
        fetch.assert_not_called()
        limit.assert_not_called()

    def test_rate_limit_stops_download(self):
        with patch.object(guest, "fetch") as fetch, patch.object(
            guest, "check_rate_limit", side_effect=guest.GuestError("Try again later", status=429),
        ):
            response = self.client.post("/public/download", json={
                "url": "https://example.com/clip.mp4", "quality": "480",
            })
        self.assertEqual(response.status_code, 429)
        fetch.assert_not_called()

    def test_limits_are_public(self):
        response = self.client.get("/public/limits")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["qualities"], ["720", "480"])


if __name__ == "__main__":
    unittest.main()
