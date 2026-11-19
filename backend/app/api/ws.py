import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.database import SessionLocal
from app.models import Download
from app.schemas import DownloadOut
from app.security import decode_token

router = APIRouter()

POLL_SECONDS = 1.0


def _snapshot(user_id: int) -> list[dict]:
    db = SessionLocal()
    try:
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
    """Push the user's download list whenever it changes (~1s resolution).

    Auth via ?token= since browsers cannot set headers on WebSocket connects.
    """
    try:
        user_id = int(decode_token(token or "")["sub"])
    except Exception:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    last: list[dict] | None = None
    try:
        while True:
            snap = await run_in_threadpool(_snapshot, user_id)
            if snap != last:
                await websocket.send_json({"type": "snapshot", "items": snap})
                last = snap
            await asyncio.sleep(POLL_SECONDS)
    except (WebSocketDisconnect, RuntimeError):
        pass
