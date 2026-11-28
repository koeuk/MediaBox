import json
import unittest
from unittest.mock import Mock, patch

import yt_dlp
from yt_dlp.utils import ExtractorError

from app.services.facebook import (
    FacebookStoryIE, _selected_video_id, extract_info, story_parts,
)


TOKEN = "UzpfSVNDOjMwODU0ODc3NTUxMjIyOTQ="
URL = f"https://web.facebook.com/stories/120270149829745/{TOKEN}/?view_single=1"


def story(ident, video_id):
    return {"id": ident, "attachments": [{"media": {
        "__typename": "Video", "id": video_id,
    }}]}


class FacebookStoryTests(unittest.TestCase):
    def test_shared_link_and_encoded_token_are_recognized(self):
        self.assertEqual(story_parts(URL), ("120270149829745", TOKEN))
        self.assertEqual(story_parts(URL.replace("=/?", "%3D/?")), story_parts(URL))

    def test_other_hosts_and_non_story_urls_are_not_matched(self):
        for url in (
            URL.replace("web.facebook.com", "facebook.com.example.org"),
            URL.replace("web.facebook.com", "notfacebook.com"),
            URL.replace("https:", "ftp:"),
            "https://www.facebook.com/reel/123",
            "https://www.facebook.com/stories/123/",
        ):
            with self.subTest(url=url):
                self.assertIsNone(story_parts(url))

    def test_only_requested_story_is_selected_from_multiple_edges(self):
        data = {"edges": [
            {"node": story("other-story", "111")},
            {"node": story(TOKEN, "222")},
        ]}
        self.assertEqual(_selected_video_id([data], TOKEN), "222")

    def test_decoded_story_id_is_supported(self):
        self.assertEqual(_selected_video_id([
            story("3085487755122294", "222")], TOKEN), "222")
        self.assertEqual(_selected_video_id([
            story("S:_ISC:3085487755122294", "222")], TOKEN), "222")

    def test_missing_story_does_not_download_an_unrelated_video(self):
        self.assertIsNone(_selected_video_id([story("other-story", "111")], TOKEN))

    def test_story_page_resolves_its_actual_video_id(self):
        page = '<script type="application/json">' + json.dumps(story(TOKEN, "222")) + '</script>'
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            ie = FacebookStoryIE(ydl)
            with patch.object(ie, "_download_webpage", return_value=page):
                result = ie._real_extract(URL)
        self.assertEqual(result["url"], "https://www.facebook.com/watch/?v=222")
        self.assertEqual(result["ie_key"], "Facebook")

    def test_login_and_expired_stories_have_clear_errors(self):
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            ie = FacebookStoryIE(ydl)
            for page, message in (("<form id='login_form'>", "requires login"),
                                  ("<html></html>", "expired")):
                with self.subTest(message=message), patch.object(
                    ie, "_download_webpage", return_value=page,
                ), self.assertRaisesRegex(ExtractorError, message):
                    ie._real_extract(URL)

    def test_custom_extractor_is_explicitly_selected_before_generic(self):
        ydl = Mock()
        extract_info(ydl, URL)
        ydl.extract_info.assert_called_once_with(
            URL, download=True, ie_key=FacebookStoryIE.ie_key())
        self.assertIsInstance(ydl.add_info_extractor.call_args.args[0], FacebookStoryIE)

    def test_existing_video_links_use_normal_extraction(self):
        ydl = Mock()
        url = "https://www.facebook.com/watch/?v=222"
        extract_info(ydl, url)
        ydl.add_info_extractor.assert_not_called()
        ydl.extract_info.assert_called_once_with(url, download=True)


if __name__ == "__main__":
    unittest.main()
