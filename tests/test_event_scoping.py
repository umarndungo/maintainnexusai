"""SSE visibility checks across station and cross-station roles."""
import asyncio
import json

from api.events import events, publish_event


class ConnectedRequest:
    async def is_disconnected(self):
        return False


def test_engineer_stream_excludes_other_and_unknown_stations():
    async def check():
        response = await events(ConnectedRequest(), {"id": "engineer", "role": "engineer", "station_ids": ["STATION-1"]})
        stream = response.body_iterator
        assert "event: ready" in await anext(stream)
        publish_event({"type": "update", "station_id": "STATION-2", "work_order_id": "OTHER"})
        publish_event({"type": "update", "work_order_id": "UNSCOPED"})
        publish_event({"type": "update", "station_id": "STATION-1", "work_order_id": "OWN"})
        try:
            message = await asyncio.wait_for(anext(stream), timeout=1)
            payload = json.loads(message.split("data: ", 1)[1])
            assert payload["work_order_id"] == "OWN"
        finally:
            await stream.aclose()
    asyncio.run(check())


def test_executive_stream_receives_cross_station_events():
    async def check():
        response = await events(ConnectedRequest(), {"id": "executive", "role": "executive", "station_ids": []})
        stream = response.body_iterator
        await anext(stream)
        publish_event({"type": "update", "station_id": "STATION-2", "work_order_id": "NETWORK"})
        try:
            assert "NETWORK" in await asyncio.wait_for(anext(stream), timeout=1)
        finally:
            await stream.aclose()
    asyncio.run(check())
