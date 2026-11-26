import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import admin, downloads, ws
from app.database import Base, get_db
from app.models import AppSetting, Download, DownloadStatus, User
from app.permissions import can, get_defaults
from app.security import create_access_token, create_media_token


class ApiQueryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.user = User(email='perf@example.com', username='perf', hashed_password='unused')
        self.db.add(self.user)
        self.db.commit()
        self.user_id = self.user.id
        self.queries = []
        event.listen(self.engine, 'before_cursor_execute', self.record_query)

    def record_query(self, conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            self.queries.append(statement)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_permissions_share_one_query_and_do_not_leak_mutations(self):
        for permission in ('media.view', 'media.create', 'media.edit', 'media.delete'):
            self.assertTrue(can(self.user, permission))
        defaults = get_defaults(self.db)
        defaults['media.view'] = False
        self.assertTrue(can(self.user, 'media.view'))
        self.assertEqual(len(self.queries), 1)

    def test_permissions_refresh_after_commit_and_rollback(self):
        self.assertTrue(can(self.user, 'media.view'))
        self.db.add(AppSetting(key='default_perm:media.view', value='0'))
        self.db.commit()
        self.assertFalse(can(self.user, 'media.view'))
        self.db.rollback()
        with Session(self.engine) as other:
            other.get(AppSetting, 'default_perm:media.view').value = '1'
            other.commit()
        self.assertTrue(can(self.user, 'media.view'))

    def test_stats_use_three_queries_and_preserve_counts(self):
        for status, size, favorite in (
            (DownloadStatus.completed, 1234, True),
            (DownloadStatus.completed, 66, False),
            (DownloadStatus.failed, 900, True),
            (DownloadStatus.downloading, 100, False),
            (DownloadStatus.queued, 0, False),
        ):
            self.db.add(Download(user_id=self.user_id, url='https://example.com/media',
                                 status=status, downloaded_bytes=size, is_favorite=favorite))
        self.db.commit()
        self.queries.clear()
        result = admin.stats(self.db, self.user)
        self.assertEqual(len(self.queries), 3)
        self.assertEqual((result.downloads, result.favorites, result.bytes_stored), (5, 2, 1300))
        self.assertEqual((result.completed, result.failed, result.downloading, result.queued), (2, 1, 1, 1))

    def test_stats_empty_library(self):
        result = admin.stats(self.db, self.user)
        self.assertEqual((result.downloads, result.favorites, result.bytes_stored), (0, 0, 0))

    def test_database_session_closes_before_file_stream_starts(self):
        self.db.commit()
        sessions = []
        streamed = []

        def request_db():
            session = Session(self.engine)
            sessions.append(session)
            try:
                yield session
            finally:
                session.close()

        test = self

        class CheckedFileResponse(FileResponse):
            async def __call__(self, scope, receive, send):
                test.assertEqual(len(sessions), 1, 'Auth and handler must share one session')
                test.assertFalse(sessions[0].in_transaction(), 'Connection is held during streaming')
                streamed.append(True)
                await super().__call__(scope, receive, send)

        with tempfile.TemporaryDirectory() as parent:
            path = Path(parent) / 'test.mp4'
            path.write_bytes(b'test-media')
            row = Download(user_id=self.user_id, url='https://example.com/media',
                           status=DownloadStatus.completed, file_path=str(path), filename=path.name)
            self.db.add(row)
            self.db.commit()
            ident = row.id
            self.db.commit()
            app = FastAPI()
            app.include_router(downloads.router, prefix='/downloads')
            app.dependency_overrides[get_db] = request_db
            with patch.object(downloads, 'FileResponse', CheckedFileResponse), TestClient(app) as client:
                response = client.get(f'/downloads/{ident}/file?token={create_media_token(self.user_id)}')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b'test-media')
            self.assertEqual(streamed, [True])


class ProgressSocketTests(unittest.IsolatedAsyncioTestCase):
    async def test_idle_disconnect_stops_polling_immediately(self):
        sent = asyncio.Event()
        socket = Mock()
        socket.accept = AsyncMock()
        socket.close = AsyncMock()

        async def send_json(payload):
            sent.set()

        async def receive():
            await sent.wait()
            return {'type': 'websocket.disconnect'}

        socket.send_json = AsyncMock(side_effect=send_json)
        socket.receive = AsyncMock(side_effect=receive)
        with patch.object(ws, '_snapshot', return_value=[]) as snapshot, \
                patch.object(ws, 'IDLE_POLL_SECONDS', 60):
            await asyncio.wait_for(ws.progress_ws(socket, create_media_token(123)), timeout=1)
        snapshot.assert_called_once_with(123, 0)
        socket.send_json.assert_awaited_once_with({'type': 'snapshot', 'items': []})

    async def test_active_download_keeps_fast_poll_interval(self):
        socket = Mock()
        socket.accept = AsyncMock()
        socket.close = AsyncMock()
        socket.send_json = AsyncMock()

        async def receive():
            await asyncio.Future()

        socket.receive = AsyncMock(side_effect=receive)
        intervals = []

        async def stop_after_interval(future, timeout):
            intervals.append(timeout)
            raise asyncio.CancelledError()

        with patch.object(ws, '_snapshot', return_value=[{'status': 'downloading'}]), \
                patch.object(ws.asyncio, 'wait_for', side_effect=stop_after_interval):
            with self.assertRaises(asyncio.CancelledError):
                await ws.progress_ws(socket, create_media_token(123))
        self.assertEqual(intervals, [ws.POLL_SECONDS])


if __name__ == '__main__':
    unittest.main()
