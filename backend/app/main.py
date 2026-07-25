from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  (register models with the metadata)
from app.api import admin, auth, categories, downloads, ws
from app.config import settings
from app.database import Base, engine, run_migrations
from app.services import jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        run_migrations(conn)
    jobs.reset_interrupted()
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
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(ws.router, tags=["ws"])


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}
