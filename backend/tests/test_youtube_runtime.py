import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.config import settings
from app.services import extractor, guest


class YoutubeRuntimeTests(unittest.TestCase):
    def test_member_and_guest_enable_available_node_and_solver(self):
        def available(name):
            return '/usr/local/bin/node' if name == 'node' else None

        with patch.object(extractor.shutil, 'which', side_effect=available), \
                patch.object(settings, 'ytdlp_remote_components', ' ejs:github '), \
                patch.object(settings, 'ytdlp_cookies_file', ''):
            member = extractor._build_opts(SimpleNamespace(quality='720'), '/tmp/video.mp4', lambda d: None,
                                           'https://www.youtube.com/watch?v=test')
            with tempfile.TemporaryDirectory() as parent, patch('yt_dlp.YoutubeDL') as factory:
                folder = Path(parent)
                produced = folder / 'video.mp4'
                def download(*args, **kwargs):
                    produced.write_bytes(b'video')
                factory.return_value.__enter__.return_value.extract_info.side_effect = download
                self.assertEqual(guest._fetch_ytdlp('https://www.youtube.com/watch?v=test', folder, '480'), produced)
                guest_opts = factory.call_args.args[0]
            for opts in (member, guest_opts):
                self.assertEqual(opts['js_runtimes'], {'node': {'path': None}})
                self.assertEqual(opts['remote_components'], ['ejs:github'])

    def test_disabled_remote_components_are_not_enabled(self):
        with patch.object(extractor.shutil, 'which', return_value=None), \
                patch.object(settings, 'ytdlp_remote_components', ''):
            self.assertEqual(extractor._runtime_opts(), {})

    def test_all_installed_runtimes_are_available(self):
        with patch.object(extractor.shutil, 'which', return_value='/usr/bin/runtime'), \
                patch.object(settings, 'ytdlp_remote_components', 'ejs:github, ejs:npm'):
            opts = extractor._runtime_opts()
        self.assertEqual(set(opts['js_runtimes']), {'deno', 'node', 'bun'})
        self.assertEqual(opts['remote_components'], ['ejs:github', 'ejs:npm'])


if __name__ == '__main__':
    unittest.main()
