"""Resolve a selected Facebook video story without downloading other stories."""

import base64
import binascii
import json
import re
from urllib.parse import unquote, urlparse

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.extractor.facebook import FacebookIE
from yt_dlp.utils import ExtractorError


def story_parts(url: str) -> tuple[str, str] | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or not (
        host == "facebook.com" or host.endswith(".facebook.com")
    ):
        return None
    match = re.fullmatch(r"/stories/(\d+)/([^/]+)/?", parsed.path)
    if not match:
        return None
    owner, token = match.groups()
    token = unquote(token)
    if not re.fullmatch(r"[A-Za-z0-9_+=-]{1,256}", token):
        return None
    return owner, token


def _story_ids(token: str) -> set[str]:
    ids = {token}
    try:
        decoded = base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True).decode()
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return ids
    ids.add(decoded)
    match = re.fullmatch(r"S:_ISC:(\d+)", decoded)
    if match:
        ids.add(match.group(1))
    return ids


def _objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _objects(child)


def _selected_video_id(documents, token: str) -> str | None:
    ids = _story_ids(token)
    for document in documents:
        for node in _objects(document):
            if str(node.get("id", "")) not in ids:
                continue
            # Only inspect attachments on the selected story. Other edges can
            # contain another person's story, recommendations, or adverts.
            for attachment in node.get("attachments") or []:
                for media in _objects(attachment):
                    ident = str(media.get("id", ""))
                    if media.get("__typename") == "Video" and re.fullmatch(r"\d+", ident):
                        return ident
    return None


class FacebookStoryIE(InfoExtractor):
    IE_NAME = "mediabox:facebook:story"
    _VALID_URL = r"https?://(?:[\w-]+\.)?facebook\.com/stories/(?P<owner>\d+)/(?P<id>[^/?#]+)"

    def _real_extract(self, url):
        owner, token = story_parts(url)
        page = self._download_webpage(
            f"https://www.facebook.com/stories/{owner}/{token}/?view_single=1", token)
        documents = []
        for script in re.findall(r"<script\b[^>]*>(.*?)</script\s*>", page, re.I | re.S):
            try:
                documents.append(json.loads(script))
            except (ValueError, TypeError):
                continue
        video_id = _selected_video_id(documents, token)
        if video_id:
            return self.url_result(
                f"https://www.facebook.com/watch/?v={video_id}", FacebookIE, video_id)
        if re.search(r'login_form|id=["\']loginbutton|name=["\']login', page, re.I):
            self.raise_login_required(
                "Facebook requires login to view this story. "
                "The server needs a valid Facebook cookies file for an account allowed to view it.")
        raise ExtractorError(
            "This Facebook story has no accessible video. It may have expired, "
            "be private, or contain only a photo.", expected=True)


def extract_info(ydl, url: str, *, download: bool = True):
    if story_parts(url):
        ydl.add_info_extractor(FacebookStoryIE())
        return ydl.extract_info(url, download=download, ie_key=FacebookStoryIE.ie_key())
    return ydl.extract_info(url, download=download)
