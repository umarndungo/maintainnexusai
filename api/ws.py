from typing import Set
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.dashboard import build_dashboard_summary

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# Keep a set of connected websockets in-memory for broadcasting.
_connections: Set[WebSocket] = set()


async def _safe_send(ws: WebSocket, message: dict):
    try:
        await ws.send_json(message)
    except Exception:
        try:
            await ws.close()
        except Exception:
            pass


async def broadcast_summary():
    """Build the current dashboard summary and send to all connected clients."""
    summary = build_dashboard_summary()
    # Send concurrently
    coros = [ _safe_send(ws, summary) for ws in list(_connections) ]
    if coros:
        await asyncio.gather(*coros, return_exceptions=True)


@router.websocket("/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await websocket.accept()
    _connections.add(websocket)
    try:
        while True:
            # Keep the connection alive by awaiting incoming messages (pings)
            # Clients are not required to send messages; this keeps the socket open.
            await websocket.receive_text()
    except WebSocketDisconnect:
        _connections.discard(websocket)
    except Exception:
        _connections.discard(websocket)
        try:
            await websocket.close()
        except Exception:
            pass
