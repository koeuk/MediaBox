import smtplib
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.orm import Session

import test_access_mode
from app.api import auth
from app.config import settings
from app.database import run_migrations
from app.models import User
from app.security import create_media_token, hash_password, verify_password
from app.services import password_reset


class PasswordResetTests(unittest.TestCase):
    def setUp(self):
        test_access_mode.AccessModeTests.setUp(self)
        self.client.app.include_router(auth.router, prefix='/auth')
        self.member.hashed_password = hash_password('old-password')
        self.db.commit()
        patch.multiple(settings, smtp_host='smtp.gmail.com', smtp_port=587, smtp_username='sender@example.com',
                       smtp_password=SecretStr('app-password'), smtp_from_email='sender@example.com',
                       smtp_use_ssl=False, frontend_url='https://mediabox.example', password_reset_expire_minutes=30).start()
        self.send = patch('app.services.password_reset.deliver').start()

    tearDown = test_access_mode.AccessModeTests.tearDown

    def request(self, email='member@example.com'):
        return self.client.post('/auth/forgot-password', json={'email': email})

    def token(self):
        return parse_qs(urlsplit(self.send.call_args.args[1]).fragment)['token'][0]

    def reset(self, token, password='new-password'):
        return self.client.post('/auth/reset-password', json={'token': token, 'new_password': password})

    def test_reset_email_is_generic_token_hashed_and_link_trusted(self):
        missing = self.request('missing@example.com')
        self.send.assert_not_called()
        existing = self.request()
        self.assertEqual(existing.status_code, 200)
        self.assertEqual(existing.json(), missing.json())
        self.assertEqual(self.send.call_args.args[0], 'member@example.com')
        link = urlsplit(self.send.call_args.args[1])
        self.assertEqual((link.scheme, link.netloc, link.path, link.query), ('https', 'mediabox.example', '/reset-password', ''))
        token = self.token()
        self.db.refresh(self.member)
        self.assertEqual(self.member.password_reset_hash, password_reset.token_digest(token, self.member))
        self.assertNotEqual(self.member.password_reset_hash, token)
        self.assertNotIn(token, existing.text)
        self.assertGreater(self.member.password_reset_expires_at.replace(tzinfo=timezone.utc), datetime.now(timezone.utc) + timedelta(minutes=29))

    def test_password_reset_is_single_use_and_old_sessions_are_revoked(self):
        old_media = create_media_token(self.member.id)
        self.request()
        token = self.token()
        response = self.reset(token)
        self.assertEqual(response.status_code, 200, response.text)
        self.db.refresh(self.member)
        self.assertTrue(verify_password('new-password', self.member.hashed_password))
        self.assertFalse(verify_password('old-password', self.member.hashed_password))
        self.assertIsNone(self.member.password_reset_hash)
        self.assertEqual(self.member.session_version, 1)
        self.assertEqual(self.reset(token).status_code, 400)
        self.assertEqual(self.client.get('/auth/me', headers=self.member_headers).status_code, 401)
        self.assertEqual(self.client.get('/auth/me/avatar', params={'token': old_media}).status_code, 401)
        old_login = self.client.post('/auth/login', json={'email': self.member.email, 'password': 'old-password'})
        self.assertEqual(old_login.status_code, 401)
        login = self.client.post('/auth/login', json={'email': self.member.email, 'password': 'new-password'})
        self.assertEqual(login.status_code, 200)
        headers = {'Authorization': f"Bearer {login.json()['access_token']}"}
        self.assertEqual(self.client.get('/auth/me', headers=headers).status_code, 200)
        media = self.client.post('/auth/media-token', headers=headers)
        self.assertEqual(media.status_code, 200)
        self.assertEqual(self.client.get('/auth/me/avatar', params={'token': media.json()['token']}).status_code, 404)
        from app.api.ws import _snapshot
        with patch('app.api.ws.SessionLocal', return_value=Session(self.engine)):
            with self.assertRaises(PermissionError):
                _snapshot(self.member.id, 0)

    def test_reset_token_cannot_authenticate_api_requests(self):
        self.request()
        token = self.token()
        self.assertEqual(self.client.get('/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code, 401)
        self.assertEqual(self.reset(self.member_headers['Authorization'].split(' ', 1)[1]).status_code, 400)

    def test_expired_tampered_and_malformed_links_fail(self):
        self.request()
        token = self.token()
        altered = token[:-1] + ('a' if token[-1] != 'a' else 'b')
        self.assertEqual(self.reset(altered).status_code, 400)
        for invalid in ('x' * 50, '9' * 19 + '.' + 'x' * 43, '999999.' + 'x' * 43):
            self.assertEqual(self.reset(invalid).status_code, 400)
        self.db.refresh(self.member)
        self.member.password_reset_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.db.commit()
        self.assertEqual(self.reset(token).status_code, 400)
        self.assertTrue(verify_password('old-password', self.member.hashed_password))

    def test_repeat_requests_are_throttled_and_new_link_replaces_old(self):
        self.request()
        old = self.token()
        self.request()
        self.assertEqual(self.send.call_count, 1)
        self.db.refresh(self.member)
        self.member.password_reset_requested_at = datetime.now(timezone.utc) - timedelta(seconds=61)
        self.db.commit()
        self.request()
        self.assertEqual(self.send.call_count, 2)
        new = self.token()
        self.assertNotEqual(old, new)
        self.assertEqual(self.reset(old).status_code, 400)
        self.assertEqual(self.reset(new).status_code, 200)

    def test_password_and_email_changes_invalidate_links(self):
        for changes in ({'email': 'changed@example.com'}, {'new_password': 'admin-password'}):
            self.member.email = 'member@example.com'
            self.member.password_reset_requested_at = None
            self.db.commit()
            self.request()
            token = self.token()
            response = self.client.patch(f'/admin/users/{self.member.id}', json=changes, headers=self.admin_headers)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(self.reset(token).status_code, 400)

    def test_suspended_accounts_do_not_receive_or_use_reset_links(self):
        self.request()
        token = self.token()
        self.member.is_suspended = True
        self.db.commit()
        response = self.request()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.send.call_count, 1)
        self.assertEqual(self.reset(token).status_code, 400)

    def test_validation_and_unconfigured_email(self):
        self.assertEqual(self.request('invalid-email').status_code, 422)
        self.request()
        self.assertEqual(self.reset(self.token(), 'short').status_code, 422)
        self.assertEqual(self.reset(self.token(), 'x' * 129).status_code, 422)
        with patch.object(settings, 'smtp_password', SecretStr('')):
            existing = self.request()
            missing = self.request('missing@example.com')
            self.assertEqual(existing.status_code, 503)
            self.assertEqual(existing.json(), missing.json())

    def test_admin_email_reset_requires_manage_access(self):
        path = f'/admin/users/{self.member.id}/password-reset'
        self.assertEqual(self.client.post(path, headers=self.member_headers).status_code, 403)
        self.assertEqual(self.client.post(path).status_code, 401)
        self.assertEqual(self.client.post(path, headers=self.admin_headers).status_code, 200)
        self.send.assert_called_once()
        self.client.patch(f'/admin/users/{self.member.id}', json={'permissions': {'users.view': True, 'users.edit': True}}, headers=self.admin_headers)
        self.assertEqual(self.client.post(f'/admin/users/{self.admin.id}/password-reset', headers=self.member_headers).status_code, 403)

    def test_migration_is_repeatable_and_existing_sessions_keep_version_zero(self):
        with self.engine.begin() as conn:
            for name in ('session_version', 'password_reset_hash', 'password_reset_expires_at', 'password_reset_requested_at'):
                conn.execute(text(f'ALTER TABLE users DROP COLUMN {name}'))
            run_migrations(conn)
            run_migrations(conn)
            row = conn.execute(text('SELECT session_version, password_reset_hash FROM users LIMIT 1')).one()
            self.assertEqual(row.session_version, 0)
            self.assertIsNone(row.password_reset_hash)

    def test_manual_admin_reset_also_revokes_old_sessions(self):
        response = self.client.patch(f'/admin/users/{self.member.id}', json={'new_password': 'manual-password'}, headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/auth/me', headers=self.member_headers).status_code, 401)
        login = self.client.post('/auth/login', json={'email': self.member.email, 'password': 'manual-password'})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.get('/auth/me', headers={'Authorization': f"Bearer {login.json()['access_token']}"}).status_code, 200)

    def test_profile_password_change_revokes_old_sessions(self):
        response = self.client.patch('/auth/me', json={'current_password': 'old-password', 'new_password': 'profile-password'}, headers=self.member_headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.get('/auth/me', headers=self.member_headers).status_code, 401)
        login = self.client.post('/auth/login', json={'email': self.member.email, 'password': 'profile-password'})
        self.assertEqual(login.status_code, 200)


class SmtpDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.original = password_reset.deliver
        self.config = patch.multiple(settings, smtp_host='smtp.gmail.com', smtp_port=587, smtp_username='sender@example.com', smtp_password=SecretStr('app-password'), smtp_from_email='sender@example.com', smtp_use_ssl=False)
        self.config.start()

    def tearDown(self):
        self.config.stop()

    def test_starttls_authenticated_message(self):
        with patch('app.services.password_reset.smtplib.SMTP') as smtp:
            self.original('recipient@example.com', 'https://mediabox.example/reset-password#token=secret')
            client = smtp.return_value.__enter__.return_value
            client.starttls.assert_called_once()
            client.login.assert_called_once_with('sender@example.com', 'app-password')
            message = client.send_message.call_args.args[0]
            self.assertEqual(message['To'], 'recipient@example.com')
            self.assertIn('#token=secret', message.get_content())
            self.assertNotIn('app-password', message.get_content())

    def test_ssl_transport_and_safe_error_logging(self):
        with patch.object(settings, 'smtp_use_ssl', True), patch('app.services.password_reset.smtplib.SMTP_SSL') as smtp:
            self.original('recipient@example.com', 'https://example.com/reset-password#token=secret')
            smtp.return_value.__enter__.return_value.starttls.assert_not_called()
            smtp.return_value.__enter__.return_value.send_message.assert_called_once()
        with patch('app.services.password_reset.smtplib.SMTP', side_effect=smtplib.SMTPAuthenticationError(535, b'secret-error')):
            with self.assertLogs('app.services.password_reset', level='ERROR') as logs:
                self.original('recipient@example.com', 'https://example.com/#token=secret')
            output = '\n'.join(logs.output)
            self.assertNotIn('secret', output)
            self.assertNotIn('recipient@example.com', output)
            self.assertNotIn('app-password', output)
