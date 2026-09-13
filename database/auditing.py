"""Append-only hash-chained audit log writes."""

import hashlib
import json
from datetime import datetime, timezone

from database.models import AuditLog

GENESIS_HASH = "GENESIS"


def append_audit_log(db, event_name: str, payload: dict) -> AuditLog:
    """Insert an audit row without ever mutating an existing row."""
    previous = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    if previous is not None and not previous.event_hash:
        raise RuntimeError(
            "Cannot append to an unchained audit log; preserve legacy rows and migrate them under DBA review"
        )
    timestamp = datetime.now(timezone.utc)
    previous_hash = previous.event_hash if previous else GENESIS_HASH
    serialized = json.dumps(
        {
            "event_name": event_name,
            "payload": payload,
            "timestamp": timestamp.isoformat(),
            "supersedes_event_id": None,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    event = AuditLog(
        event_name=event_name,
        payload=json.dumps(payload),
        timestamp=timestamp,
        previous_event_hash=previous_hash,
        event_hash=hashlib.sha256((serialized + previous_hash).encode()).hexdigest(),
    )
    db.add(event)
    return event