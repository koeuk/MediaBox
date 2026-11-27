import unittest
from unittest.mock import Mock, patch

import manage_spaces
from app.config import settings


class SpacesManagementTests(unittest.TestCase):
    def test_cors_update_retains_unrelated_rules(self):
        client = Mock()
        other = {"ID": "another-app", "AllowedOrigins": ["https://other.example"], "AllowedMethods": ["GET"]}
        client.get_bucket_cors.return_value = {"CORSRules": [other, {"ID": "mediabox-test"}]}
        with patch.object(settings, "app_env", "test"), \
                patch.object(manage_spaces.object_store, "get_spaces_client", return_value=client), \
                patch("builtins.print"):
            manage_spaces.configure_cors(["https://droplinks.site"])
        rules = client.put_bucket_cors.call_args.kwargs["CORSConfiguration"]["CORSRules"]
        self.assertEqual(rules[0], other)
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[1]["AllowedOrigins"], ["https://droplinks.site"])
        self.assertEqual(rules[1]["AllowedMethods"], ["GET", "HEAD"])

    def test_storage_check_cleans_test_object_on_failure(self):
        client = Mock()
        client.upload_fileobj.side_effect = RuntimeError("failed write")
        with patch.object(manage_spaces.object_store, "get_spaces_client", return_value=client):
            with self.assertRaises(RuntimeError):
                manage_spaces.check()
        client.delete_object.assert_called_once()

    def test_cors_rejects_non_origin_urls_before_remote_calls(self):
        with patch.object(manage_spaces.object_store, "get_spaces_client") as client:
            with self.assertRaises(ValueError):
                manage_spaces.configure_cors(["https://droplinks.site/path"])
        client.assert_not_called()
