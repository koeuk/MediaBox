from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  (register models with the metadata)
from app.api import admin, auth, downloads, ws
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Download, DownloadStatus


def _migrate(connection) -> None:
    """Minimal in-place migrations (create_all only creates missing tables)."""
    from sqlalchemy import inspect, text

    columns = {c["name"] for c in inspect(connection).get_columns("downloads")}
    for name, ddl in [
        ("quality", "quality VARCHAR(8)"),
        ("convert_source", "convert_source TEXT"),
        ("convert_target", "convert_target VARCHAR(8)"),
    ]:
        if name not in columns:
            connection.execute(text(f"ALTER TABLE downloads ADD COLUMN {ddl}"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        _migrate(conn)
    # the job queue is in-memory, so anything in-flight when the previous
    # process died is marked failed — /retry resumes from the partial file
    db = SessionLocal()
    try:
        stuck = (
            db.query(Download)
            .filter(Download.status.in_([DownloadStatus.queued, DownloadStatus.downloading]))
            .all()
        )
        for dl in stuck:
            dl.status = DownloadStatus.failed
            dl.error = "Interrupted by a server restart — retry to resume"
        db.commit()
    finally:
        db.close()
    yield


app = FastAPI(title=f"{settings.app_name} API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(downloads.router, prefix="/api/downloads", tags=["downloads"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(ws.router, tags=["ws"])


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}
