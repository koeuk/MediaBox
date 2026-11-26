import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.database import SessionLocal
from app.models import Download, DownloadStatus, User
from app.permissions import can
from app.schemas import DownloadOut
from app.security import decode_token

router = APIRouter()

POLL_SECONDS = 1.0
IDLE_POLL_SECONDS = 5.0


def _snapshot(user_id: int, version: int | None = None) -> list[dict]:
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if user is None or user.is_suspended or not can(user, "media.view") or (version is not None and user.session_version != version):
            raise PermissionError("Media access denied")
        rows = (
            db.query(Download)
            .filter(Download.user_id == user_id)
            .order_by(Download.created_at.desc())
            .all()
        )
        return [DownloadOut.model_validate(r).model_dump(mode="json") for r in rows]
    finally:
        db.close()


@router.websocket("/api/ws/progress")
async def progress_ws(websocket: WebSocket, token: str | None = None):
    """Push changes every second during active jobs, every five seconds idle.

    Auth via ?token= since browsers cannot set headers on WebSocket connects.
    """
    try:
        payload = decode_token(token or "")
        user_id = int(payload["sub"])
        version = payload.get("ver", 0)
    except Exception:
        await websocket.close(code=4401)
        return

    await websocket.accept()

    async def wait_for_disconnect():
        # A send-only socket otherwise keeps querying forever after an idle
        # client disconnects, because unchanged snapshots never trigger a send.
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return

    disconnected = asyncio.create_task(wait_for_disconnect())
    last: list[dict] | None = None
    try:
        while not disconnected.done():
            snap = await run_in_threadpool(_snapshot, user_id, version)
            if snap != last:
                await websocket.send_json({"type": "snapshot", "items": snap})
                last = snap
            active = any(item["status"] in (DownloadStatus.queued, DownloadStatus.downloading) for item in snap)
            interval = POLL_SECONDS if active else IDLE_POLL_SECONDS
            try:
                await asyncio.wait_for(asyncio.shield(disconnected), timeout=interval)
            except asyncio.TimeoutError:
                pass
    except PermissionError:
        await websocket.close(code=4403)
    except (WebSocketDisconnect, RuntimeError, OSError):
        pass
    finally:
        disconnected.cancel()
        await asyncio.gather(disconnected, return_exceptions=True)
