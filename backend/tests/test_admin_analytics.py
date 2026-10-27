"""Run with: python -m unittest discover -s tests -v (from backend/)."""

import unittest
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.admin import router
from app.database import Base, get_db
from app.models import Download, DownloadStatus, User
from app.security import create_access_token


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


class AdminAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.admin = self.add_user("admin", "2026-01-01T00:00:00", is_admin=True)
        self.member = self.add_user("member", "2026-01-31T23:59:59.999999")
        self.add_user("march", "2026-03-15T12:00:00")
        for timestamp, status in [
            ("2025-12-31T23:59:59.999999", DownloadStatus.completed),
            ("2026-01-01T00:00:00", DownloadStatus.completed),
            ("2026-01-31T23:59:59.999999", DownloadStatus.failed),
            ("2026-03-01T00:00:00", DownloadStatus.queued),
            ("2026-03-31T23:59:59.999999", DownloadStatus.downloading),
            ("2026-04-01T00:00:00", DownloadStatus.completed),
        ]:
            self.add_download(timestamp, status)
        self.db.commit()

        app = FastAPI()
        app.include_router(router, prefix="/admin")

        def test_db():
            yield self.db

        app.dependency_overrides[get_db] = test_db
        self.client = TestClient(app)
        self.headers = {"Authorization": f"Bearer {create_access_token(self.admin.id)}"}

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def add_user(self, name, timestamp, **kwargs):
        user = User(
            email=f"{name}@example.com", username=name, hashed_password="unused",
            created_at=utc(timestamp), **kwargs,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def add_download(self, timestamp, status=DownloadStatus.completed):
        self.db.add(Download(
            user_id=self.admin.id, url="https://example.com/video.mp4",
            title=timestamp, created_at=utc(timestamp), status=status,
        ))

    def get(self, path="/analytics", **params):
        return self.client.get(f"/admin{path}", params=params, headers=self.headers)

    def test_monthly_counts_include_all_statuses_and_zero_months(self):
        response = self.get(start_date="2026-01-01", end_date="2026-03-31")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "start_date": "2026-01-01", "end_date": "2026-03-31",
            "months": [
                {"month": "2026-01-01", "downloads": 2, "new_users": 2},
                {"month": "2026-02-01", "downloads": 0, "new_users": 0},
                {"month": "2026-03-01", "downloads": 2, "new_users": 1},
            ],
        })

    def test_single_day_includes_start_and_end_boundaries(self):
        for day in ("2026-01-01", "2026-01-31"):
            with self.subTest(day=day):
                params = {"start_date": day, "end_date": day}
                month = self.get(**params).json()["months"][0]
                self.assertEqual((month["downloads"], month["new_users"]), (1, 1))
                rows = self.get("/downloads", **params).json()
                self.assertEqual(len(rows), 1)
                self.assertTrue(rows[0]["created_at"].startswith(day))

    def test_partial_month_only_counts_selected_dates(self):
        response = self.get(start_date="2026-01-15", end_date="2026-03-01")
        self.assertEqual([month["downloads"] for month in response.json()["months"]], [1, 0, 1])
        self.assertEqual([month["new_users"] for month in response.json()["months"]], [1, 0, 0])

    def test_year_boundary_and_leap_day(self):
        self.add_download("2024-02-29T23:59:59.999999")
        self.db.commit()
        response = self.get(start_date="2023-12-01", end_date="2024-03-01")
        self.assertEqual([month["month"] for month in response.json()["months"]], [
            "2023-12-01", "2024-01-01", "2024-02-01", "2024-03-01",
        ])
        self.assertEqual([month["downloads"] for month in response.json()["months"]], [0, 0, 1, 0])

    def test_chart_counts_are_not_limited_by_recent_downloads(self):
        for _ in range(25):
            self.add_download("2026-01-15T12:00:00")
        self.db.commit()
        params = {"start_date": "2026-01-01", "end_date": "2026-01-31"}
        self.assertEqual(self.get(**params).json()["months"][0]["downloads"], 27)
        self.assertEqual(len(self.get("/downloads", limit=20, **params).json()), 20)

    def test_empty_range(self):
        params = {"start_date": "2030-01-01", "end_date": "2030-01-31"}
        self.assertEqual(self.get(**params).json()["months"], [
            {"month": "2030-01-01", "downloads": 0, "new_users": 0},
        ])
        self.assertEqual(self.get("/downloads", **params).json(), [])

    def test_invalid_ranges(self):
        for path in ("/analytics", "/downloads"):
            for params in (
                {"start_date": "2026-02-01", "end_date": "2026-01-01"},
                {"start_date": "not-a-date"},
                {"end_date": "2026-02-30"},
            ):
                with self.subTest(path=path, params=params):
                    self.assertEqual(self.get(path, **params).status_code, 422)
        self.assertEqual(self.get(start_date="2016-01-01", end_date="2026-01-01").status_code, 422)
        self.assertEqual(self.get(start_date="2016-01-01", end_date="2025-12-31").status_code, 200)

    def test_defaults_cover_twelve_months_through_end_date(self):
        data = self.get(end_date="2026-03-15").json()
        self.assertEqual(data["start_date"], "2025-04-01")
        self.assertEqual(data["end_date"], "2026-03-15")
        self.assertEqual(len(data["months"]), 12)
        self.assertEqual(self.get(end_date="0001-01-01").status_code, 200)

    def test_recent_downloads_support_one_sided_ranges(self):
        before = self.get("/downloads", end_date="2026-01-01").json()
        self.assertEqual(len(before), 2)
        after = self.get("/downloads", start_date="2026-03-31").json()
        self.assertEqual(len(after), 2)
        self.assertEqual(len(self.get("/downloads").json()), 6)
        self.assertEqual(self.get("/downloads", limit=0).status_code, 422)

    def test_admin_authentication_is_required(self):
        for path in ("/analytics", "/downloads"):
            self.assertEqual(self.client.get(f"/admin{path}").status_code, 401)
            headers = {"Authorization": f"Bearer {create_access_token(self.member.id)}"}
            self.assertEqual(self.client.get(f"/admin{path}", headers=headers).status_code, 403)


if __name__ == "__main__":
    unittest.main()
