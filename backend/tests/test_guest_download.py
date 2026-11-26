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


class PinterestGuestTests(unittest.TestCase):
    def test_short_image_pin_downloads_image_instead_of_webpage(self):
        image_url = "https://i.pinimg.com/originals/example.jpg"

        def save_image(url, dest, limit):
            dest.write_bytes(b"pin-image")
            return 9, "image/jpeg"

        with patch.object(guest.pinterest, "resolve_share_link", return_value=(
            "https://www.pinterest.com/pin/901705156665736533/sent/?sender=123"
        )) as resolve, patch.object(guest.pinterest, "_fetch_pin", return_value={
            "images": {"orig": {"url": image_url}},
        }), patch.object(guest.pinterest, "_download_image", side_effect=save_image) as download, \
                patch.object(guest, "_fetch_direct") as direct, \
                patch.object(guest, "_fetch_ytdlp") as video:
            path, folder = guest.fetch("https://pin.it/340gITu40", "480")
            try:
                self.assertEqual(path.name, "pinterest-901705156665736533.jpg")
                self.assertEqual(path.read_bytes(), b"pin-image")
                resolve.assert_called_once_with("https://pin.it/340gITu40")
                download.assert_called_once_with(image_url, path, guest.storage.max_bytes())
                direct.assert_not_called()
                video.assert_not_called()
            finally:
                guest.shutil.rmtree(folder)

    def test_video_pin_preserves_guest_quality_and_uses_canonical_url(self):
        with tempfile.TemporaryDirectory() as parent:
            folder = Path(parent)
            with patch.object(guest.pinterest, "_fetch_pin", return_value={
                "videos": {"video_list": {"V_720P": {"url": "https://example.com/video.mp4"}}},
            }), patch.object(guest, "_fetch_ytdlp", return_value=folder / "clip.mp4") as video:
                guest._fetch_pinterest("https://www.pinterest.com/pin/123/sent/", folder, "720")
            video.assert_called_once_with("https://www.pinterest.com/pin/123/", folder, "720")

    def test_failed_image_download_removes_temporary_files(self):
        destinations = []

        def fail_image(url, dest, limit):
            destinations.append(dest)
            dest.write_bytes(b"partial")
            raise ValueError("This pin exceeds the size limit")

        with patch.object(guest.pinterest, "_fetch_pin", return_value={
            "images": {"orig": {"url": "https://i.pinimg.com/originals/example.jpg"}},
        }), patch.object(guest.pinterest, "_download_image", side_effect=fail_image):
            with self.assertRaisesRegex(guest.GuestError, "size limit"):
                guest.fetch("https://www.pinterest.com/pin/123/", "480")
        self.assertEqual(len(destinations), 1)
        self.assertFalse(destinations[0].parent.exists())


if __name__ == "__main__":
    unittest.main()
