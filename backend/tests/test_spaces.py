import unittest
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.deps import get_current_user
from app.api.spaces import get_spaces_client, router
from app.config import settings
from app.models import User


class SpacesTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.s3 = Mock()
        self.app.dependency_overrides[get_spaces_client] = lambda: self.s3
        self.app.dependency_overrides[get_current_user] = lambda: User(
            id=7, email="test@example.com", username="test", is_admin=True
        )
        self.client = TestClient(self.app)

    def test_upload_and_sign_private_file(self):
        response = self.client.post(
            "/upload", files={"file": ("../photo.png", b"image data", "image/png")}
        )
        self.assertEqual(response.status_code, 200)
        key = response.json()["key"]
        self.assertTrue(key.startswith("uploads/7/"))
        self.assertTrue(key.endswith("-photo.png"))
        self.assertNotIn("..", key)
        args, kwargs = self.s3.upload_fileobj.call_args
        self.assertEqual(args[1:], (settings.do_spaces_bucket, key))
        self.assertEqual(kwargs["ExtraArgs"], {"ContentType": "image/png"})

        self.s3.generate_presigned_url.return_value = "https://example.com/signed"
        response = self.client.get(f"/url/{key}")
        self.assertEqual(response.json(), {"url": "https://example.com/signed"})
        self.s3.generate_presigned_url.assert_called_once_with(
            "get_object", Params={"Bucket": settings.do_spaces_bucket, "Key": key},
            ExpiresIn=3600,
        )

    def test_cannot_sign_another_users_file(self):
        for key in ("uploads/8/private.txt", "uploads/70/private.txt", "other/file.txt"):
            with self.subTest(key=key):
                self.assertEqual(self.client.get(f"/url/{key}").status_code, 404)
        self.s3.generate_presigned_url.assert_not_called()

    def test_authentication_required(self):
        del self.app.dependency_overrides[get_current_user]
        self.assertEqual(self.client.post("/upload", files={"file": ("x", b"x")}).status_code, 401)
        self.assertEqual(self.client.get("/url/uploads/7/x").status_code, 401)

    def test_upload_limit_prevents_remote_write(self):
        with patch.object(settings, "max_download_size_mb", 0):
            response = self.client.post("/upload", files={"file": ("x", b"x")})
        self.assertEqual(response.status_code, 413)
        self.s3.upload_fileobj.assert_not_called()

    def test_storage_error_is_not_exposed(self):
        self.s3.upload_fileobj.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "internal details"}}, "PutObject"
        )
        with self.assertLogs("app.api.spaces", level="ERROR"):
            response = self.client.post("/upload", files={"file": ("x", b"x")})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("internal details", response.text)

    def test_unconfigured_spaces_returns_service_unavailable(self):
        del self.app.dependency_overrides[get_spaces_client]
        with patch.object(settings, "do_spaces_key", SecretStr("")):
            response = self.client.get("/url/uploads/7/x")
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
