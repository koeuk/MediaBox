import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth import router as auth_router
from app.database import Base, get_db
from app.models import User
from app.security import create_access_token, hash_password


class HiddenPasswordTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

        self.user = User(
            id=1,
            email="test@example.com",
            username="tester",
            hashed_password=hash_password("accountpass123"),
            is_admin=False,
        )
        self.db.add(self.user)
        self.db.commit()

        app = FastAPI()
        app.include_router(auth_router, prefix="/auth")

        def test_db():
            yield self.db

        app.dependency_overrides[get_db] = test_db
        self.client = TestClient(app)
        self.headers = {"Authorization": f"Bearer {create_access_token(self.user.id)}"}

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def test_set_verify_and_remove_hidden_password(self):
        # 1. User initially has no hidden password
        res = self.client.post(
            "/auth/verify-hidden-password",
            json={"password": "any"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"unlocked": True})

        # 2. Set hidden password
        res = self.client.put(
            "/auth/me/hidden-password",
            json={"new_password": "secret_hidden_123"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["has_hidden_password"])

        # 3. Verify fails with wrong password
        res = self.client.post(
            "/auth/verify-hidden-password",
            json={"password": "wrong"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 400)

        # 4. Verify succeeds with hidden password
        res = self.client.post(
            "/auth/verify-hidden-password",
            json={"password": "secret_hidden_123"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"unlocked": True})

        # 5. Verify also succeeds with main account password (fallback)
        res = self.client.post(
            "/auth/verify-hidden-password",
            json={"password": "accountpass123"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"unlocked": True})

        # 6. Change hidden password directly (no current password needed)
        res = self.client.put(
            "/auth/me/hidden-password",
            json={"new_password": "brand_new_pass"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)

        # 7. Old hidden password no longer works
        res = self.client.post(
            "/auth/verify-hidden-password",
            json={"password": "secret_hidden_123"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 400)

        # 8. New hidden password works
        res = self.client.post(
            "/auth/verify-hidden-password",
            json={"password": "brand_new_pass"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)

        # 9. Remove hidden password directly without current password
        res = self.client.post(
            "/auth/me/hidden-password/remove",
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["has_hidden_password"])
