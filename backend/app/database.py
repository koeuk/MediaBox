from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# pool_pre_ping revalidates pooled connections — avoids "MySQL server has
# gone away" after idle periods (harmless for SQLite/Postgres)
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations(conn) -> None:
    """Add columns that create_all can't (it only creates missing tables).

    Runs against a live connection so callers control the transaction.
    """
    from sqlalchemy import inspect, text

    columns = {c["name"] for c in inspect(conn).get_columns("downloads")}
    for name, ddl in [
        ("quality", "quality VARCHAR(8)"),
        ("convert_source", "convert_source TEXT"),
        ("convert_target", "convert_target VARCHAR(8)"),
        ("category", "category VARCHAR(50)"),
        ("job_kind", "job_kind VARCHAR(16)"),
    ]:
        if name not in columns:
            conn.execute(text(f"ALTER TABLE downloads ADD COLUMN {ddl}"))
