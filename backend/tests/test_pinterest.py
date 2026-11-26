import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services import guest, pinterest


def carousel_pin():
    return {
        "is_video": False,
        "videos": None,
        "images": {"orig": {"url": "https://i.pinimg.com/cover.jpg"}},
        "carousel_data": {"carousel_slots": [{
            "videos": {"video_list": {
                "V_720P": {"url": "https://v1.pinimg.com/clip.mp4", "height": 720},
                "V_HLSV4": {"url": "https://v1.pinimg.com/clip.m3u8", "height": 720},
            }},
        }]},
    }


class PinterestCarouselTests(unittest.TestCase):
    def test_image_story_is_not_mistaken_for_video(self):
        data = {
            "story_pin_data": {"pages": [{
                "video": None,
                "blocks": [{"type": "story_pin_image_block", "image": {}}],
            }]},
        }
        self.assertFalse(pinterest._has_video(data))

    def test_video_story_is_detected_in_blocks_and_pages(self):
        video = {"video_list": {"V_720P": {"url": "https://v1.pinimg.com/clip.mp4"}}}
        for page in ({"video": video}, {"blocks": [{"video": video}]}):
            with self.subTest(page=page):
                self.assertTrue(pinterest._has_video({"story_pin_data": {"pages": [page]}}))

    def test_guest_image_story_downloads_original_image(self):
        data = {
            "story_pin_data": {"pages": [{"video": None, "blocks": [{"image": {}}]}]},
            "images": {"orig": {"url": "https://i.pinimg.com/originals/photo.jpg"}},
        }
        with tempfile.TemporaryDirectory() as parent:
            folder = Path(parent)
            with patch.object(pinterest, "_fetch_pin", return_value=data), \
                    patch.object(guest, "_fetch_ytdlp") as video, \
                    patch.object(pinterest, "_download_image") as image:
                path = guest._fetch_pinterest("https://www.pinterest.com/pin/1132233162601206298/", folder, "480")
            self.assertEqual(path.suffix, ".jpg")
            image.assert_called_once_with("https://i.pinimg.com/originals/photo.jpg", path, guest.storage.max_bytes())
            video.assert_not_called()

    def test_nested_video_is_detected_despite_top_level_flags(self):
        data = carousel_pin()
        self.assertTrue(pinterest._has_video(data))
        self.assertEqual(pinterest._carousel_video_url(data), "https://v1.pinimg.com/clip.m3u8")

    def test_image_carousel_still_uses_images(self):
        data = carousel_pin()
        data["carousel_data"]["carousel_slots"][0]["videos"] = None
        self.assertFalse(pinterest._has_video(data))
        self.assertEqual(pinterest._best_image(data), "https://i.pinimg.com/cover.jpg")

    def test_guest_routes_carousel_video_to_media_url_with_quality(self):
        with tempfile.TemporaryDirectory() as parent:
            folder = Path(parent)
            with patch.object(pinterest, "_fetch_pin", return_value=carousel_pin()), \
                    patch.object(guest, "_fetch_ytdlp", return_value=folder / "clip.mp4") as video, \
                    patch.object(pinterest, "_download_image") as image:
                guest._fetch_pinterest("https://www.pinterest.com/pin/123/", folder, "480")
            video.assert_called_once_with("https://v1.pinimg.com/clip.m3u8", folder, "480")
            image.assert_not_called()

    def test_member_routes_carousel_video_to_media_url(self):
        dl = SimpleNamespace(id=1, url="https://www.pinterest.com/pin/123/")
        db = Mock()
        with patch.object(pinterest, "_fetch_pin", return_value=carousel_pin()), \
                patch("app.services.extractor.run_ytdlp") as video, \
                patch.object(pinterest, "_download_image") as image:
            pinterest.run_pinterest(dl, db)
        video.assert_called_once_with(dl, db, url="https://v1.pinimg.com/clip.m3u8")
        image.assert_not_called()


if __name__ == "__main__":
    unittest.main()
