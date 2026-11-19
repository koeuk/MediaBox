import unittest
from datetime import datetime, timedelta, timezone

import test_access_mode
from app.models import PaymentRequest, PaymentStatus, Plan, User
from app.security import verify_password


class AdminCreationTests(unittest.TestCase):
    setUp = test_access_mode.AccessModeTests.setUp
    tearDown = test_access_mode.AccessModeTests.tearDown

    def permissions(self, values):
        return self.client.patch(f'/admin/users/{self.member.id}', json={'permissions': values}, headers=self.admin_headers)

    def user_payload(self, **changes):
        return dict(username='new user', email='new@example.com', password='initial-password', **changes)

    def plan_payload(self):
        return dict(code='quarter', label='3 months', days=90, price=12.50, is_free=False)

    def test_admin_creates_member_that_can_sign_in(self):
        response = self.client.post('/admin/users', json=self.user_payload(), headers=self.admin_headers)
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()
        self.assertFalse(data['is_admin'])
        self.assertIsNone(data['permissions'])
        self.assertEqual(data['download_count'], 0)
        self.assertNotIn('password', data)
        user = self.db.get(User, data['id'])
        self.assertTrue(verify_password('initial-password', user.hashed_password))
        from app.api import auth
        self.client.app.include_router(auth.router, prefix='/auth')
        login = self.client.post('/auth/login', json={'email': 'new@example.com', 'password': 'initial-password'})
        self.assertEqual(login.status_code, 200, login.text)
        self.assertEqual(login.json()['user']['id'], user.id)

    def test_user_creation_validation_duplicate_and_auth(self):
        self.assertEqual(self.client.post('/admin/users', json=self.user_payload(), headers=self.member_headers).status_code, 403)
        self.assertEqual(self.client.post('/admin/users', json=self.user_payload()).status_code, 401)
        self.assertEqual(self.client.post('/admin/users', json=self.user_payload(), headers=self.admin_headers).status_code, 201)
        self.assertEqual(self.client.post('/admin/users', json=self.user_payload(), headers=self.admin_headers).status_code, 409)
        for changes in ({'username': ' '}, {'password': 'short'}, {'email': 'not-email'}):
            payload = self.user_payload()
            payload.update(changes)
            self.assertEqual(self.client.post('/admin/users', json=payload, headers=self.admin_headers).status_code, 422)

    def test_only_full_admin_can_create_admins(self):
        self.permissions({'users.view': True, 'users.create': True})
        self.assertEqual(self.client.post('/admin/users', json=self.user_payload(is_admin=True), headers=self.member_headers).status_code, 403)
        self.assertEqual(self.client.post('/admin/users', json=self.user_payload(), headers=self.member_headers).status_code, 201)
        payload = self.user_payload(is_admin=True)
        payload['email'] = 'newadmin@example.com'
        response = self.client.post('/admin/users', json=payload, headers=self.admin_headers)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertTrue(response.json()['is_admin'])

    def test_creating_accounts_cannot_bypass_restrictions(self):
        self.permissions({'users.view': True, 'users.create': True, 'media.create': False})
        self.assertEqual(self.client.post('/admin/users', json=self.user_payload(), headers=self.member_headers).status_code, 403)
        other = User(email='other@example.com', username='other', hashed_password='unused')
        self.db.add(other)
        self.db.commit()
        self.permissions({'users.view': True, 'users.edit': True, 'media.create': False})
        self.assertEqual(self.client.patch(f'/admin/users/{other.id}', json={'new_password': 'takeover'}, headers=self.member_headers).status_code, 403)

    def test_create_and_remove_plan_preserves_history_and_subscription(self):
        response = self.client.post('/admin/plans', json=self.plan_payload(), headers=self.admin_headers)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['days'], 90)
        self.assertTrue(any(p['code'] == 'quarter' for p in self.client.get('/public/plans').json()))
        self.member.premium_until = datetime.now(timezone.utc) + timedelta(days=90)
        receipt = PaymentRequest(user_id=self.member.id, plan_code='quarter', method='cash', amount=12.50, status=PaymentStatus.approved)
        self.db.add(receipt)
        self.db.commit()
        expiry = self.member.premium_until
        response = self.client.delete('/admin/plans/quarter', headers=self.admin_headers)
        self.assertEqual(response.status_code, 204, response.text)
        self.assertNotIn('quarter', [p['code'] for p in self.client.get('/public/plans').json()])
        self.assertNotIn('quarter', [p['code'] for p in self.client.get('/admin/plans', headers=self.admin_headers).json()])
        self.db.refresh(self.member)
        self.assertEqual(self.member.premium_until, expiry)
        self.assertIsNotNone(self.db.get(PaymentRequest, receipt.id))
        self.assertEqual(self.client.get('/admin/payments', params={'pending_only': False}, headers=self.admin_headers).json()[0]['plan_label'], '3 months')
        self.assertEqual(self.client.patch('/admin/plans/quarter', json={'price': 20}, headers=self.admin_headers).status_code, 404)
        self.assertEqual(self.client.patch(f'/admin/users/{self.member.id}', json={'plan': 'quarter'}, headers=self.admin_headers).status_code, 404)
        self.assertEqual(self.client.post('/payments', json={'plan_code': 'quarter', 'method': 'cash'}, headers=self.member_headers).status_code, 404)
        self.assertEqual(self.client.post('/admin/plans', json=self.plan_payload(), headers=self.admin_headers).status_code, 409)

    def test_plan_actions_have_independent_permissions(self):
        payload = self.plan_payload()
        self.permissions({'plans.view': True})
        self.assertEqual(self.client.post('/admin/plans', json=payload, headers=self.member_headers).status_code, 403)
        self.assertEqual(self.client.delete('/admin/plans/week', headers=self.member_headers).status_code, 403)
        self.permissions({'plans.view': True, 'plans.create': True})
        self.assertEqual(self.client.post('/admin/plans', json=payload, headers=self.member_headers).status_code, 201)
        self.assertEqual(self.client.delete('/admin/plans/quarter', headers=self.member_headers).status_code, 403)
        self.permissions({'plans.view': True, 'plans.delete': True})
        self.assertEqual(self.client.delete('/admin/plans/quarter', headers=self.member_headers).status_code, 204)

    def test_plan_validation_and_removed_builtin_stays_removed_after_seed(self):
        from app.services import plans
        for changes in ({'code': 'bad code'}, {'label': ' '}, {'days': 0}, {'days': 1.5}, {'price': -1}):
            payload = self.plan_payload()
            payload.update(changes)
            self.assertEqual(self.client.post('/admin/plans', json=payload, headers=self.admin_headers).status_code, 422)
        self.assertEqual(self.client.delete('/admin/plans/week', headers=self.admin_headers).status_code, 204)
        plans.seed(self.db)
        self.assertNotIn('week', [p.code for p in plans.listing(self.db)])

    def test_migration_adds_active_flag_without_changing_existing_plans(self):
        from sqlalchemy import text
        from app.database import run_migrations
        with self.engine.begin() as conn:
            conn.execute(text('ALTER TABLE plans DROP COLUMN is_active'))
            run_migrations(conn)
            run_migrations(conn)
            row = conn.execute(text("SELECT price, is_active FROM plans WHERE code = 'week'")).one()
            self.assertEqual(row.price, 5)
            self.assertTrue(row.is_active)
