"""Run from backend: python manage_spaces.py --help. No secrets or signed URLs printed."""

import argparse
import io

import httpx
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.services import object_store


def check():
    """Round-trip a private test object and always try to remove it."""
    client = object_store.get_spaces_client()
    key = object_store.new_key(0, "storage-check.txt", kind="checks")
    payload = b"MediaBox Spaces verification\n"
    try:
        client.upload_fileobj(io.BytesIO(payload), settings.do_spaces_bucket, key,
                              ExtraArgs={"ContentType": "text/plain"})
        client.head_object(Bucket=settings.do_spaces_bucket, Key=key)
        url = object_store.signed_url(object_store.reference_for(key))
        with httpx.Client(timeout=30) as http:
            response = http.get(url, headers={"Origin": str(settings.frontend_url).rstrip("/")})
            response.raise_for_status()
            if response.content != payload:
                raise RuntimeError("Downloaded content did not match the upload")
            if response.headers.get("access-control-allow-origin") not in (
                str(settings.frontend_url).rstrip("/"), "*",
            ):
                raise RuntimeError("Upload/download works, but bucket CORS is missing for FRONTEND_URL")
            # Drop query parameters to verify the object cannot be read publicly.
            if http.get(url.split("?", 1)[0]).status_code not in (401, 403, 404):
                raise RuntimeError("Test object is publicly accessible; check bucket permissions")
        print("PASS: private upload, metadata, signed download, content, and browser CORS")
    finally:
        client.delete_object(Bucket=settings.do_spaces_bucket, Key=key)
    print("PASS: test object deleted")


def configure_cors(origins):
    """Keep other bucket rules and replace only this environment's managed rule."""
    from urllib.parse import urlparse

    for origin in origins:
        parsed = urlparse(origin)
        if parsed.scheme not in ("https", "http") or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
            raise ValueError("Origins must be exact URLs such as https://droplinks.site (no trailing slash)")
    client = object_store.get_spaces_client()
    try:
        rules = client.get_bucket_cors(Bucket=settings.do_spaces_bucket)["CORSRules"]
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") not in ("NoSuchCORSConfiguration", "NoSuchCORS"):
            raise
        rules = []
    rule_id = f"mediabox-{settings.app_env}"
    rules = [rule for rule in rules if rule.get("ID") != rule_id]
    rules.append({
        "ID": rule_id, "AllowedOrigins": origins, "AllowedMethods": ["GET", "HEAD"],
        "AllowedHeaders": ["Range"],
        "ExposeHeaders": ["Content-Length", "Content-Range", "Content-Disposition", "Accept-Ranges"],
        "MaxAgeSeconds": 3600,
    })
    client.put_bucket_cors(Bucket=settings.do_spaces_bucket, CORSConfiguration={"CORSRules": rules})
    print(f"Configured browser reads for {settings.app_env}; unrelated CORS rules retained")


def migrate(apply):
    """Run with workers stopped and after a DB/media backup. Retain local backups."""
    from app.database import SessionLocal
    from app.models import Download, DownloadStatus
    from app.services import storage

    if settings.storage_backend != "spaces":
        raise ValueError("Set STORAGE_BACKEND=spaces before migration")
    with SessionLocal() as db:
        ids = [row[0] for row in db.query(Download.id).filter(Download.status == DownloadStatus.completed).all()]
        count = 0
        for ident in ids:
            dl = db.get(Download, ident)
            paths = [dl.file_path, dl.thumbnail_path, *dl.slide_paths]
            local = [p for p in paths if p and not object_store.is_remote(p)]
            if not local:
                continue
            if not all(storage.exists(p) for p in local):
                raise ValueError(f"Record {ident} has missing local files; restore them before migrating")
            count += 1
            if apply:
                storage.persist_media(db, dl, keep_local=True)
            print(f"{'Migrated' if apply else 'Would migrate'} record {ident}")
        print(f"{count} record(s). Local originals retained; database backup is needed for rollback.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="Verify private upload, signed download, CORS, and deletion")
    cors = commands.add_parser("configure-cors", help="Update the bucket's browser read permissions")
    cors.add_argument("--origin", action="append", required=True)
    migration = commands.add_parser("migrate", help="Preview completed-library migration (read only by default)")
    migration.add_argument("--apply", action="store_true", help="Upload objects and update DB references, retaining local originals")
    args = parser.parse_args()
    try:
        if args.command == "check":
            check()
        elif args.command == "configure-cors":
            configure_cors(args.origin)
        else:
            migrate(args.apply)
    except (object_store.StorageError, BotoCoreError, ClientError, httpx.HTTPError, RuntimeError, ValueError):
        # SDK/HTTP errors can contain signed URLs or configuration details.
        parser.exit(1, "Spaces operation failed. Check credentials, permissions, environment, connectivity, and bucket CORS.\n")


if __name__ == "__main__":
    main()
