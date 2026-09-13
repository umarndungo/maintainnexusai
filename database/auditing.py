"""Append-only hash-chained audit log writes."""

import hashlib
import json
from datetime import datetime, timezone

from database.models import AuditLog
from database.timeutils import to_utc

GENESIS_HASH = "GENESIS"


def _canonical_audit_data(record: AuditLog) -> dict:
    """The exact fields hashed for one audit row. Shared by the writer here
    and by the /dashboard/audit-logs/verify endpoint, so a hash computed
    from a freshly-queried row always agrees with the one computed at
    insert time."""
    return {
        "event_name": record.event_name,
        "payload": json.loads(record.payload),
        "timestamp": to_utc(record.timestamp).isoformat(),
        "supersedes_event_id": record.supersedes_event_id,
    }


def compute_audit_hash(record: AuditLog, previous_hash: str) -> str:
    serialized = json.dumps(_canonical_audit_data(record), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((serialized + previous_hash).encode("utf-8")).hexdigest()


def append_audit_log(db, event_name: str, payload: dict) -> AuditLog:
    """Insert an audit row without ever mutating an existing row."""
    previous = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    if previous is not None and not previous.event_hash:
        raise RuntimeError(
            "Cannot append to an unchained audit log; preserve legacy rows and migrate them under DBA review"
        )
    previous_hash = previous.event_hash if previous else GENESIS_HASH
    event = AuditLog(
        event_name=event_name,
        payload=json.dumps(payload),
        timestamp=datetime.now(timezone.utc),
        previous_event_hash=previous_hash,
        supersedes_event_id=None,
    )
    event.event_hash = compute_audit_hash(event, previous_hash)
    db.add(event)
    return event