"""Append-only lifecycle writes and status derivation."""

import hashlib
import json
from datetime import datetime, timezone

from database.models import WorkOrderLifecycleEvent

GENESIS_HASH = "GENESIS"


def _canonical_event_data(event: WorkOrderLifecycleEvent) -> str:
    return json.dumps(
        {
            "work_order_id": event.work_order_id,
            "from_status": event.from_status,
            "to_status": event.to_status,
            "actor_id": event.actor_id,
            "actor_role": event.actor_role,
            "timestamp": event.timestamp.isoformat(),
            "note": event.note,
            "supersedes_event_id": event.supersedes_event_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def append_lifecycle_event(
    db,
    *,
    work_order_id: str,
    to_status: str,
    actor_id: str,
    actor_role: str,
    from_status: str | None = None,
    note: str | None = None,
    supersedes_event_id: int | None = None,
) -> WorkOrderLifecycleEvent:
    """Insert one transition; this function never updates or deletes history."""
    previous = (
        db.query(WorkOrderLifecycleEvent)
        .order_by(WorkOrderLifecycleEvent.id.desc())
        .first()
    )
    event = WorkOrderLifecycleEvent(
        work_order_id=work_order_id,
        from_status=from_status,
        to_status=to_status,
        actor_id=actor_id,
        actor_role=actor_role,
        timestamp=datetime.now(timezone.utc),
        note=note,
        previous_event_hash=previous.event_hash if previous else GENESIS_HASH,
        supersedes_event_id=supersedes_event_id,
        event_hash="pending",
    )
    event.event_hash = hashlib.sha256(
        (_canonical_event_data(event) + event.previous_event_hash).encode("utf-8")
    ).hexdigest()
    db.add(event)
    return event


def current_work_order_status(db, work_order_id: str) -> str | None:
    event = (
        db.query(WorkOrderLifecycleEvent)
        .filter(WorkOrderLifecycleEvent.work_order_id == work_order_id)
        .order_by(WorkOrderLifecycleEvent.id.desc())
        .first()
    )
    return event.to_status if event else None