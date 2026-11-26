import unittest

import yt_dlp

from app.services.formats import limit_video_quality


def video(ident, width, height, muxed=False):
    return {
        'format_id': ident,
        'url': f'https://example.com/{ident}.mp4',
        'ext': 'mp4', 'width': width, 'height': height,
        'vcodec': 'avc1.4d401f', 'acodec': 'mp4a.40.2' if muxed else 'none',
    }


AUDIO = {'format_id': 'audio', 'url': 'https://example.com/audio.m4a',
         'ext': 'm4a', 'vcodec': 'none', 'acodec': 'mp4a.40.2'}


class VideoQualityTests(unittest.TestCase):
    def select(self, formats, quality):
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'format': 'bv*+ba/b'}) as ydl:
            limit_video_quality(ydl, quality)
            return ydl.process_ie_result({
                'id': 'test', 'title': 'Test', 'formats': formats,
                'extractor': 'test', 'extractor_key': 'Test',
            }, download=False)

    def test_portrait_720_selects_best_720_width_and_audio(self):
        result = self.select([
            AUDIO,
            video('360p', 360, 640), video('540p', 540, 960),
            video('720p', 720, 1280), video('1080p', 1080, 1920),
        ], '720')
        self.assertEqual((result['width'], result['height']), (720, 1280))
        self.assertEqual([f['format_id'] for f in result['requested_formats']], ['720p', 'audio'])

    def test_landscape_720_selects_best_720_height(self):
        result = self.select([
            AUDIO,
            video('360p', 640, 360), video('720p', 1280, 720), video('1080p', 1920, 1080),
        ], '720')
        self.assertEqual((result['width'], result['height']), (1280, 720))

    def test_480_selects_lower_portrait_rendition(self):
        result = self.select([AUDIO, video('360p', 360, 640), video('720p', 720, 1280)], '480')
        self.assertEqual(result['width'], 360)

    def test_muxed_portrait_needs_no_separate_audio(self):
        result = self.select([video('720p', 720, 1280, muxed=True)], '720')
        self.assertEqual(result['format_id'], '720p')
        self.assertNotIn('requested_formats', result)

    def test_unknown_and_above_limit_formats_do_not_bypass_cap(self):
        with self.assertRaisesRegex(yt_dlp.utils.ExtractorError, 'Requested format is not available'):
            self.select([AUDIO, video('unknown', None, None, muxed=True),
                         video('1080p', 1080, 1920)], '720')

    def test_best_available_still_selects_full_resolution(self):
        result = self.select([AUDIO, video('720p', 720, 1280), video('1080p', 1080, 1920)], None)
        self.assertEqual(result['width'], 1080)

    def test_1080_cap_does_not_allow_4k_portrait(self):
        result = self.select([AUDIO, video('1080p', 1080, 1920), video('4k', 2160, 3840)], '1080')
        self.assertEqual(result['width'], 1080)


if __name__ == '__main__':
    unittest.main()
