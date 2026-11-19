import unittest

import test_access_mode
from app.models import User


class UserPermissionsTests(unittest.TestCase):
    setUp = test_access_mode.AccessModeTests.setUp
    tearDown = test_access_mode.AccessModeTests.tearDown

    def set_role(self, user, is_admin, headers=None):
        return self.client.patch(f'/admin/users/{user.id}', json={'is_admin': is_admin}, headers=headers or self.admin_headers)

    def test_define_role_and_restore_member(self):
        self.assertFalse(self.member.is_admin)
        response = self.set_role(self.member, True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['is_admin'])
        self.assertEqual(self.client.get('/admin/users', headers=self.member_headers).status_code, 200)
        response = self.set_role(self.member, False)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_admin'])
        self.assertEqual(self.client.get('/admin/users', headers=self.member_headers).status_code, 403)
        self.db.refresh(self.member)
        self.assertFalse(self.member.is_admin)

    def test_member_cannot_change_roles(self):
        self.assertEqual(self.set_role(self.member, True, self.member_headers).status_code, 403)
        self.db.refresh(self.member)
        self.assertFalse(self.member.is_admin)

    def test_admin_cannot_reset_own_role(self):
        self.assertEqual(self.set_role(self.admin, False).status_code, 400)
        self.db.refresh(self.admin)
        self.assertTrue(self.admin.is_admin)

    def test_last_active_admin_cannot_be_demoted(self):
        self.member.is_admin = True
        self.member.is_suspended = True
        self.db.commit()
        # A suspended admin still cannot remove the sole active admin, even
        # when the handler receives a trusted administrator dependency.
        from app.api.admin import update_user
        from app.schemas import AdminUserEdit
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as caught:
            update_user(self.admin.id, AdminUserEdit(is_admin=False), self.db, self.member)
        self.assertEqual(caught.exception.status_code, 400)
        self.assertTrue(self.db.get(User, self.admin.id).is_admin)

    def permissions(self, values):
        return self.client.patch(f'/admin/users/{self.member.id}', json={'permissions': values}, headers=self.admin_headers)

    def test_feedback_view_only_cannot_mutate_or_read_other_sections(self):
        response = self.permissions({'feedback.view': True})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['permissions'], {'feedback.view': True})
        self.assertEqual(self.client.get('/admin/feedback', headers=self.member_headers).status_code, 200)
        for path in ('users', 'plans', 'payments', 'downloads', 'stats', 'analytics', 'payment-settings', 'access-settings'):
            self.assertEqual(self.client.get(f'/admin/{path}', headers=self.member_headers).status_code, 403, path)
        self.assertEqual(self.client.post('/admin/feedback', json={'body': 'Hello'}, headers=self.member_headers).status_code, 403)
        self.assertEqual(self.client.patch('/admin/feedback/1', json={'body': 'Changed'}, headers=self.member_headers).status_code, 403)
        self.assertEqual(self.client.delete('/admin/feedback/1', headers=self.member_headers).status_code, 403)

    def test_feedback_actions_are_independent(self):
        self.permissions({'feedback.view': True, 'feedback.create': True})
        response = self.client.post('/admin/feedback', json={'body': 'Hello'}, headers=self.member_headers)
        self.assertEqual(response.status_code, 201, response.text)
        item_id = response.json()['id']
        self.assertEqual(self.client.patch(f'/admin/feedback/{item_id}', json={'body': 'Updated'}, headers=self.member_headers).status_code, 403)
        self.permissions({'feedback.view': True, 'feedback.edit': True})
        self.assertEqual(self.client.patch(f'/admin/feedback/{item_id}', json={'body': 'Updated'}, headers=self.member_headers).status_code, 200)
        self.assertEqual(self.client.delete(f'/admin/feedback/{item_id}', headers=self.member_headers).status_code, 403)
        self.permissions({'feedback.view': True, 'feedback.delete': True})
        self.assertEqual(self.client.delete(f'/admin/feedback/{item_id}', headers=self.member_headers).status_code, 204)

    def test_view_required_and_reset_revokes_delegated_access(self):
        self.permissions({'feedback.create': True})
        self.assertEqual(self.client.post('/admin/feedback', json={'body': 'Hello'}, headers=self.member_headers).status_code, 403)
        self.permissions({'feedback.view': True})
        self.permissions(None)
        self.assertEqual(self.client.get('/admin/feedback', headers=self.member_headers).status_code, 403)

    def test_users_editor_cannot_escalate_or_take_over_privileged_accounts(self):
        self.permissions({'users.view': True, 'users.edit': True, 'users.delete': True})
        for target, body in ((self.member, {'is_admin': True}), (self.member, {'permissions': None}), (self.admin, {'new_password': 'compromised'})):
            response = self.client.patch(f'/admin/users/{target.id}', json=body, headers=self.member_headers)
            self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self.client.delete(f'/admin/users/{self.admin.id}', headers=self.member_headers).status_code, 403)

    def test_overrides_validate_and_self_restriction_is_blocked(self):
        for values in ({'unknown.view': True}, {'feedback.view': 'yes'}, {'feedback.view': None}):
            self.assertEqual(self.permissions(values).status_code, 422)
        response = self.client.patch(f'/admin/users/{self.admin.id}', json={'permissions': {'users.edit': False}}, headers=self.admin_headers)
        self.assertEqual(response.status_code, 400)

    def test_admin_overrides_and_full_admin_guard(self):
        self.set_role(self.member, True)
        self.permissions({'feedback.delete': False})
        self.assertEqual(self.client.get('/admin/feedback', headers=self.member_headers).status_code, 200)
        self.assertEqual(self.client.delete('/admin/feedback/1', headers=self.member_headers).status_code, 403)
        self.assertEqual(self.client.patch(f'/admin/users/{self.admin.id}', json={'permissions': None}, headers=self.member_headers).status_code, 403)

    def test_permissions_persist_and_migrate_with_role_defaults(self):
        from sqlalchemy import text
        from sqlalchemy.orm import Session
        from app.database import run_migrations
        self.permissions({'feedback.view': True})
        with Session(self.engine) as other:
            self.assertEqual(other.get(User, self.member.id).permissions, {'feedback.view': True})
        with self.engine.begin() as conn:
            conn.execute(text('ALTER TABLE users DROP COLUMN permissions'))
            run_migrations(conn)
            run_migrations(conn)
            self.assertIsNone(conn.execute(text('SELECT permissions FROM users LIMIT 1')).scalar())

    def test_other_sections_support_view_without_edit(self):
        self.permissions({'plans.view': True, 'payments.view': True, 'users.view': True, 'downloads.view': True, 'dashboard.view': True})
        for path in ('plans', 'payments', 'users', 'downloads', 'stats', 'analytics', 'payment-settings', 'access-settings'):
            self.assertEqual(self.client.get(f'/admin/{path}', headers=self.member_headers).status_code, 200, path)
        for path, payload in (('plans/week', {'price': 50}), ('access-settings', {'paid_mode': False}), ('payment-settings', {'cash_enabled': False}), (f'users/{self.admin.id}', {'username': 'changed'})):
            self.assertEqual(self.client.patch(f'/admin/{path}', json=payload, headers=self.member_headers).status_code, 403, path)
        for action in ('approve', 'reject'):
            self.assertEqual(self.client.post(f'/admin/payments/1/{action}', headers=self.member_headers).status_code, 403)

    def test_full_admin_can_delete_restricted_admin(self):
        self.set_role(self.member, True)
        self.permissions({'feedback.delete': False})
        self.assertEqual(self.client.delete(f'/admin/users/{self.member.id}', headers=self.admin_headers).status_code, 204)

    def save_defaults(self, values, headers=None):
        return self.client.put('/admin/default-permissions', json={'permissions': values}, headers=headers or self.admin_headers)

    def test_shared_defaults_apply_to_existing_and_new_members(self):
        from sqlalchemy.orm import Session
        from app.models import AppSetting
        from app.permissions import STANDARD_PERMISSIONS
        self.assertEqual(self.client.get('/admin/default-permissions', headers=self.admin_headers).json(), {'permissions': STANDARD_PERMISSIONS})
        response = self.save_defaults({'feedback.view': True})
        self.assertEqual(response.status_code, 200, response.text)
        with Session(self.engine) as other:
            self.assertEqual(other.get(AppSetting, 'default_perm:feedback.view').value, '1')
        self.assertEqual(self.client.get('/admin/feedback', headers=self.member_headers).status_code, 200)
        self.assertEqual(self.client.post('/admin/feedback', json={'body': 'No create access'}, headers=self.member_headers).status_code, 403)
        newcomer = User(email='new@example.com', username='new', hashed_password='unused')
        self.db.add(newcomer)
        self.db.commit()
        from app.permissions import can
        self.assertTrue(can(newcomer, 'feedback.view'))
        self.assertFalse(can(newcomer, 'feedback.edit'))
        self.save_defaults({})
        self.assertEqual(self.client.get('/admin/feedback', headers=self.member_headers).status_code, 403)
        self.assertEqual(self.client.get('/admin/users', headers=self.admin_headers).status_code, 200)

    def test_defaults_keep_individual_overrides(self):
        self.permissions({'feedback.view': False, 'plans.view': True})
        self.save_defaults({'feedback.view': True})
        self.assertEqual(self.client.get('/admin/feedback', headers=self.member_headers).status_code, 403)
        self.assertEqual(self.client.get('/admin/plans', headers=self.member_headers).status_code, 200)
        self.db.refresh(self.member)
        self.assertEqual(self.member.permissions, {'feedback.view': False, 'plans.view': True})

    def test_defaults_require_full_admin_and_validate_actions(self):
        self.assertEqual(self.save_defaults({'feedback.view': True}, self.member_headers).status_code, 403)
        self.set_role(self.member, True)
        self.permissions({'feedback.delete': False})
        self.assertEqual(self.save_defaults({}, self.member_headers).status_code, 403)
        self.assertEqual(self.client.get('/admin/default-permissions', headers=self.member_headers).status_code, 403)
        for values in ({'unknown.view': True}, {'feedback.view': 'yes'}):
            self.assertEqual(self.save_defaults(values).status_code, 422)

    def test_auth_response_exposes_defaults_for_frontend(self):
        from app.api import auth
        self.client.app.include_router(auth.router, prefix='/auth')
        self.save_defaults({'feedback.view': True})
        response = self.client.get('/auth/me', headers=self.member_headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()['default_permissions']['feedback.view'])
        self.assertIsNone(response.json()['permissions'])

    def test_delegates_cannot_take_over_accounts_with_inherited_access(self):
        self.save_defaults({'feedback.view': True, 'feedback.create': True})
        self.permissions({'users.view': True, 'users.edit': True, 'users.delete': True, 'feedback.create': False})
        victim = User(email='victim@example.com', username='victim', hashed_password='unused')
        self.db.add(victim)
        self.db.commit()
        response = self.client.patch(f'/admin/users/{victim.id}', json={'new_password': 'takeover'}, headers=self.member_headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.delete(f'/admin/users/{victim.id}', headers=self.member_headers).status_code, 403)

    def test_user_listing_reads_shared_defaults_once(self):
        from sqlalchemy import event
        self.db.add_all(User(email=f'user{i}@example.com', username=f'user{i}', hashed_password='unused') for i in range(5))
        self.db.commit()
        queries = []
        def track(conn, cursor, statement, parameters, context, executemany):
            if 'app_settings' in statement:
                queries.append(statement)
        event.listen(self.engine, 'before_cursor_execute', track)
        try:
            response = self.client.get('/admin/users', headers=self.admin_headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(queries), 1)
        finally:
            event.remove(self.engine, 'before_cursor_execute', track)


class AccountPermissionsTests(unittest.TestCase):
    tearDown = test_access_mode.AccessModeTests.tearDown
    permissions = UserPermissionsTests.permissions
    save_defaults = UserPermissionsTests.save_defaults
    def setUp(self):
        test_access_mode.AccessModeTests.setUp(self)
        from app.api import feedback, categories, auth
        for router, prefix in ((feedback.router, '/feedback'), (categories.router, '/categories'), (auth.router, '/auth')):
            self.client.app.include_router(router, prefix=prefix)

    def test_member_actions_default_to_allowed_without_admin_access(self):
        response = self.client.get('/auth/me', headers=self.member_headers)
        self.assertEqual(response.status_code, 200)
        defaults = response.json()['default_permissions']
        for permission in ('media.view', 'media.create', 'media.edit', 'media.delete', 'categories.view', 'categories.create', 'categories.edit', 'categories.delete', 'public_feedback.view', 'public_feedback.create'):
            self.assertTrue(defaults[permission], permission)
        self.assertEqual(self.client.get('/downloads', headers=self.member_headers).status_code, 200)
        self.assertEqual(self.client.post('/downloads', json={'url': 'https://example.com/video.mp4', 'quality': '720'}, headers=self.member_headers).status_code, 201)
        self.assertEqual(self.client.post('/feedback', json={'body': 'Member feedback'}, headers=self.member_headers).status_code, 201)
        self.assertEqual(self.client.get('/admin/feedback', headers=self.member_headers).status_code, 403)

    def test_disabling_media_view_blocks_list_files_and_live_snapshot(self):
        self.permissions({'media.view': False})
        for path in ('/downloads', '/downloads/1', '/downloads/1/file', '/downloads/1/thumbnail', '/downloads/1/slide/0'):
            self.assertEqual(self.client.get(path, headers=self.member_headers).status_code, 403, path)
        from unittest.mock import patch
        from sqlalchemy.orm import Session
        from app.api.ws import _snapshot
        with patch('app.api.ws.SessionLocal', return_value=Session(self.engine)):
            with self.assertRaises(PermissionError):
                _snapshot(self.member.id)

    def test_disabling_media_create_keeps_view_and_blocks_all_creation_routes(self):
        self.permissions({'media.create': False})
        self.assertEqual(self.client.get('/downloads', headers=self.member_headers).status_code, 200)
        for path, payload in (('/downloads', {'url': 'https://example.com/video.mp4', 'quality': '720'}), ('/downloads/batch', {'urls': ['https://example.com/video.mp4'], 'quality': '720'}), ('/downloads/1/convert', {'target': 'mp3'}), ('/downloads/1/remove-background', {'quality': 'good'}), ('/downloads/1/retry', {})):
            self.assertEqual(self.client.post(path, json=payload, headers=self.member_headers).status_code, 403, path)
        self.assertEqual(self.client.post('/downloads/upload', files={'file': ('image.png', b'image', 'image/png')}, headers=self.member_headers).status_code, 403)
        self.worker.assert_not_called()

    def test_media_edit_and_delete_are_independent(self):
        from app.models import Download
        item = Download(user_id=self.member.id, url='https://example.com/video.mp4')
        self.db.add(item)
        self.db.commit()
        self.permissions({'media.edit': False, 'media.delete': False})
        for action in ('favorite', 'hide', 'category'):
            self.assertEqual(self.client.patch(f'/downloads/{item.id}/{action}', json={'category': None}, headers=self.member_headers).status_code, 403)
        self.assertEqual(self.client.delete(f'/downloads/{item.id}', headers=self.member_headers).status_code, 403)
        self.permissions({'media.edit': True, 'media.delete': False})
        self.assertEqual(self.client.patch(f'/downloads/{item.id}/favorite', headers=self.member_headers).status_code, 200)
        self.assertEqual(self.client.delete(f'/downloads/{item.id}', headers=self.member_headers).status_code, 403)

    def test_public_feedback_create_and_view_follow_permissions(self):
        self.permissions({'public_feedback.create': False})
        self.assertEqual(self.client.get('/feedback', headers=self.member_headers).status_code, 200)
        self.assertEqual(self.client.post('/feedback', json={'body': 'Blocked'}, headers=self.member_headers).status_code, 403)
        self.permissions({'public_feedback.view': False})
        self.assertEqual(self.client.get('/feedback', headers=self.member_headers).status_code, 403)
        self.assertEqual(self.client.get('/feedback/me', headers=self.member_headers).status_code, 403)
        self.assertEqual(self.client.post('/feedback', json={'body': 'Blocked'}, headers=self.member_headers).status_code, 403)
        # Public guest feedback continues to work without an account.
        self.assertEqual(self.client.get('/feedback').status_code, 200)

    def test_categories_actions_follow_permissions(self):
        self.permissions({'categories.create': False, 'categories.edit': False, 'categories.delete': False})
        self.assertEqual(self.client.get('/categories', headers=self.member_headers).status_code, 200)
        self.assertEqual(self.client.post('/categories', json={'name': 'Blocked', 'color': '#ffffff'}, headers=self.member_headers).status_code, 403)
        self.assertEqual(self.client.patch('/categories/1', json={'name': 'Blocked'}, headers=self.member_headers).status_code, 403)
        self.assertEqual(self.client.delete('/categories/1', headers=self.member_headers).status_code, 403)
        self.assertEqual(self.client.put('/categories/reorder', json=[], headers=self.member_headers).status_code, 403)

    def test_shared_member_defaults_can_disable_normal_actions(self):
        self.save_defaults({'media.create': False, 'public_feedback.create': False})
        response = self.client.get('/auth/me', headers=self.member_headers)
        self.assertFalse(response.json()['default_permissions']['media.create'])
        self.assertTrue(response.json()['default_permissions']['media.view'])
        self.assertEqual(self.client.post('/feedback', json={'body': 'Blocked'}, headers=self.member_headers).status_code, 403)
        self.permissions({'public_feedback.create': True})
        self.assertEqual(self.client.post('/feedback', json={'body': 'Allowed'}, headers=self.member_headers).status_code, 201)
