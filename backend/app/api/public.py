"""Endpoints that work without an account.

Everything here is reachable by anyone who can hit the server, so each route
is rate limited and hands back only what a visitor is allowed: low-quality
video, streamed once and not kept.
"""

import mimetypes
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.schemas import GuestDownloadRequest, GuestLimitsOut, PlanOut
from app.api.deps import DbSession
from app.services import guest, plans, storage

router = APIRouter()


@router.get("/logo")
def site_logo():
    """The uploaded site logo (navbar + favicon). 404 while none is set —
    harmless to expose: it is exactly what every page header shows anyway."""
    path = storage.find_logo()
    if not path:
        raise HTTPException(status_code=404, detail="No logo set")
    return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0] or "image/png")


@router.get("/limits", response_model=GuestLimitsOut)
def limits():
    """What the guest form is allowed to offer, so the UI need not hardcode it."""
    return GuestLimitsOut(
        qualities=list(guest.GUEST_QUALITIES),
        default_quality=guest.DEFAULT_QUALITY,
        max_size_mb=guest.settings.max_download_size_mb,
        rate_limit=guest.RATE_LIMIT,
        rate_window_seconds=guest.RATE_WINDOW_SECONDS,
    )


@router.get("/plans", response_model=list[PlanOut])
def public_plans(db: DbSession):
    """Prices for the upgrade dialog. Public: it is a price list, not a secret."""
    return plans.listing(db)


@router.post("/download")
def guest_download(payload: GuestDownloadRequest, request: Request):
    """Fetch a video and stream it straight back, keeping nothing.

    The response *is* the file, so there is no job to poll and no library row.
    Cleanup runs as a background task once the body has been sent — deleting
    the folder any earlier would pull the file out from under the response.
    """
    client_ip = request.client.host if request.client else "unknown"
    try:
        # Quality is checked before the limiter so a rejected form field costs
        # nothing — otherwise picking an unavailable quality would spend the
        # visitor's quota on a request that never downloaded anything.
        quality = guest.normalise_quality(payload.quality)
        guest.check_rate_limit(client_ip)
        path, folder = guest.fetch(str(payload.url), quality)
    except guest.GuestError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc))

    return FileResponse(
        path,
        filename=Path(path).name,
        media_type="application/octet-stream",
        background=BackgroundTask(shutil.rmtree, folder, ignore_errors=True),
    )
