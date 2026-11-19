import unittest
from unittest.mock import patch

from yt_dlp.extractor.instagram import InstagramIE

from app.config import Settings, settings
from app.services.extractor import is_ytdlp_url


class InstagramRoutingTests(unittest.TestCase):
    def test_default_hosts_route_instagram_reels_and_video_posts(self):
        urls = (
            "https://www.instagram.com/reel/Df6R7iAiD4z/?utm_source=ig_web_copy_link&fqnt=NTc4MTIwNjQ2YQ==",
            "https://instagram.com/p/Df6R7iAiD4z/",
            "https://www.instagram.com/reels/Df6R7iAiD4z/",
        )
        with patch.object(settings, "ytdlp_hosts", Settings.model_fields["ytdlp_hosts"].default):
            for url in urls:
                with self.subTest(url=url):
                    self.assertTrue(is_ytdlp_url(url))
                    self.assertTrue(InstagramIE.suitable(url))

    def test_instagram_lookalike_hosts_are_not_allowed(self):
        with patch.object(settings, "ytdlp_hosts", "instagram.com"):
            for host in ("notinstagram.com", "instagram.com.example.org"):
                with self.subTest(host=host):
                    self.assertFalse(is_ytdlp_url(f"https://{host}/reel/Df6R7iAiD4z/"))

    def test_explicit_allowlist_can_disable_instagram(self):
        with patch.object(settings, "ytdlp_hosts", "youtube.com"):
            self.assertFalse(is_ytdlp_url("https://www.instagram.com/reel/Df6R7iAiD4z/"))


if __name__ == "__main__":
    unittest.main()
