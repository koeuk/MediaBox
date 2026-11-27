from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # noqa: F401  (register models with the metadata)
from app.api import admin, auth, categories, downloads, feedback, payments, public, spaces, ws
from app.config import settings
from app.database import Base, SessionLocal, engine, run_migrations
from app.services import jobs, payments as payment_service, plans
from app.services.library import LibraryError
from app.services.object_store import StorageError


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.storage_backend == "spaces":
        from app.services.object_store import get_spaces_client
        get_spaces_client()  # Fail startup on missing credentials; never fall back to disk.
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        run_migrations(conn)
    with SessionLocal() as db:
        plans.seed(db)
        payment_service.seed_settings(db)
    jobs.reset_interrupted()
    yield


app = FastAPI(title=f"{settings.app_name} API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

@app.exception_handler(LibraryError)
@app.exception_handler(StorageError)
async def library_error_handler(request: Request, exc: LibraryError):
    """Library rejections answer in the same shape FastAPI uses for
    HTTPException, so the frontend's error handling needs no special case."""
    return JSONResponse(status_code=exc.status, content={"detail": str(exc)})


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(downloads.router, prefix="/api/downloads", tags=["downloads"])
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(public.router, prefix="/api/public", tags=["public"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])
app.include_router(ws.router, tags=["ws"])
app.include_router(spaces.router, prefix="/api", tags=["spaces"])


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}
