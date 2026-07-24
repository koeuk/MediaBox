"""One-off migration: copy users + downloads from the SQLite file into the
database pointed to by DATABASE_URL (MySQL).

Usage:
    .venv/bin/python migrate_to_mysql.py [path/to/mediabox.db]

Set DATABASE_URL in .env (or the environment) to the MySQL target first.
Safe to delete this file once the migration is done.
"""

import sys
from datetime import timezone

from sqlalchemy import MetaData, Table, create_engine, insert, select, text

from app.config import settings
from app.database import Base, engine as target_engine, run_migrations
import app.models  # noqa: F401  (register tables)

SOURCE = sys.argv[1] if len(sys.argv) > 1 else "./mediabox.db"


def naive_utc(value):
    if hasattr(value, "tzinfo") and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def main() -> None:
    if not settings.database_url.startswith("mysql"):
        sys.exit(f"DATABASE_URL is not MySQL: {settings.database_url!r} — set it in .env first")

    source_engine = create_engine(f"sqlite:///{SOURCE}")
    Base.metadata.create_all(bind=target_engine)
    with target_engine.begin() as conn:
        run_migrations(conn)
        if conn.execute(text("select count(*) from users")).scalar():
            sys.exit("Target already has users — refusing to migrate twice")

    src_meta = MetaData()
    for table in Base.metadata.sorted_tables:  # users before downloads (FK order)
        src_table = Table(table.name, src_meta, autoload_with=source_engine)
        shared = [c.name for c in table.columns if c.name in src_table.columns]
        with source_engine.connect() as src:
            rows = [
                {k: naive_utc(row[k]) for k in shared}
                for row in src.execute(select(*[src_table.c[n] for n in shared])).mappings()
            ]
        if rows:
            with target_engine.begin() as conn:
                conn.execute(insert(table), rows)
        print(f"{table.name}: {len(rows)} rows copied")

    print("Done. Restart the backend with the MySQL DATABASE_URL.")


if __name__ == "__main__":
    main()
