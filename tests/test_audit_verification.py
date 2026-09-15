"""Tests for the previously-missing /dashboard/audit-logs/verify endpoint.

07-AUDITING-GUIDE.md calls for it, and the web frontend already calls it
(``getAuditVerification`` in web/src/lib/api.ts) — but the backend route
didn't exist at all, so verification always silently came back unavailable.
These prove the endpoint actually walks both hash chains for real: a clean
chain reports intact, and a tampered row is detected and pinpointed.
"""

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.auditing import append_audit_log
from database.lifecycle import append_lifecycle_event
from database.models import AuditLog, Base, WorkOrderLifecycleEvent, WorkOrderRecord


@pytest.fixture
def verify_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr("api.dashboard.SessionLocal", session_factory)
    return session_factory


def test_verify_reports_intact_for_untampered_chains(verify_db):
    from api.dashboard import verify_audit_chain

    session = verify_db()
    session.add(WorkOrderRecord(id="WO-1", equipment_id="EQ-1", technician_id="T-1", part_number="P-1"))
    session.flush()
    append_audit_log(session, "ALERT_RECEIVED", {"equipment_id": "EQ-1"})
    append_audit_log(session, "TELEMETRY_ACCEPTED", {"equipment_id": "EQ-1", "alert_created": False})
    append_lifecycle_event(session, work_order_id="WO-1", to_status="PENDING_APPROVAL", actor_id="sys", actor_role="internal")
    append_lifecycle_event(
        session, work_order_id="WO-1", to_status="APPROVED", from_status="PENDING_APPROVAL",
        actor_id="eng-1", actor_role="engineer",
    )
    session.commit()
    session.close()

    result = asyncio.run(verify_audit_chain())

    assert result["chain_integrity"] is True
    assert result["checked_events"] == 4
    assert result["chain"] == "audit_logs+work_order_lifecycle_events"
    # Must be a real, parseable timestamp.
    datetime.fromisoformat(result["verified_at"])


def test_verify_detects_a_tampered_audit_row(verify_db):
    from api.dashboard import verify_audit_chain

    session = verify_db()
    append_audit_log(session, "ALERT_RECEIVED", {"equipment_id": "EQ-1"})
    append_audit_log(session, "TELEMETRY_ACCEPTED", {"equipment_id": "EQ-1", "alert_created": False})
    session.commit()

    # Simulate tampering: directly rewrite a persisted row's payload without
    # going through append_audit_log (which never allows this).
    tampered = session.query(AuditLog).order_by(AuditLog.id.asc()).first()
    tampered.payload = '{"equipment_id": "HACKED"}'
    session.commit()
    session.close()

    result = asyncio.run(verify_audit_chain())

    assert result["chain_integrity"] is False
    # The tampered row is the first one, so zero rows verify clean before it.
    assert result["checked_events"] == 0


def test_verify_detects_a_tampered_lifecycle_row(verify_db):
    from api.dashboard import verify_audit_chain

    session = verify_db()
    session.add(WorkOrderRecord(id="WO-1", equipment_id="EQ-1", technician_id="T-1", part_number="P-1"))
    session.flush()
    append_lifecycle_event(session, work_order_id="WO-1", to_status="PENDING_APPROVAL", actor_id="sys", actor_role="internal")
    append_lifecycle_event(
        session, work_order_id="WO-1", to_status="APPROVED", from_status="PENDING_APPROVAL",
        actor_id="eng-1", actor_role="engineer",
    )
    session.commit()

    second = (
        session.query(WorkOrderLifecycleEvent)
        .order_by(WorkOrderLifecycleEvent.id.desc())
        .first()
    )
    second.note = "rewritten after the fact"
    session.commit()
    session.close()

    result = asyncio.run(verify_audit_chain())

    assert result["chain_integrity"] is False
    # The first lifecycle row is untouched and still verifies; only the
    # second (tampered) one breaks the chain.
    assert result["checked_events"] == 1
