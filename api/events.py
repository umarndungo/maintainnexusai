"""Role-scoped server-sent events for operational changes."""

import asyncio
import json
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from api.auth import get_current_user

router = APIRouter(prefix="/api/v1/events", tags=["Events"])
_subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)


def publish_event(event: dict) -> None:
    station_id = event.get("station_id")
    for key in {"*", station_id}:
        if key is None:
            continue
        for queue in _subscribers[key]:
            queue.put_nowait(event)


@router.get("")
async def events(request: Request, user: Annotated[dict, Depends(get_current_user)]):
    queue: asyncio.Queue = asyncio.Queue()
    keys = {"*", *user.get("station_ids", [])}
    for key in keys:
        _subscribers[key].add(queue)

    async def stream():
        try:
            yield "event: ready\ndata: {}\n\n"
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    if user["role"] == "technician" and event.get("technician_id") not in {None, user["id"]}:
                        continue
                    yield f"event: {event.get('type', 'update')}\ndata: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            for key in keys:
                _subscribers[key].discard(queue)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})