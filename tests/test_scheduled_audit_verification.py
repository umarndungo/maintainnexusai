"""Tests for tasks.verify_audit_chain — the scheduled (Celery Beat) half of
audit-chain integrity checking. GET /dashboard/audit-logs/verify
(api/dashboard.py) already does this on demand — covered separately by
tests/test_audit_verification.py; this is the missing scheduled half from
07-AUDITING-GUIDE.md §3/§6, reusing the exact same api.dashboard._verify_chain
walk rather than re-deriving it.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.auditing import append_audit_log
from database.lifecycle import append_lifecycle_event
from database.models import AuditLog, Base, WorkOrderLifecycleEvent, WorkOrderRecord


@pytest.fixture
def scheduled_verify_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr("tasks.SessionLocal", session_factory)
    return session_factory


def test_scheduled_verify_reports_intact_and_writes_no_audit_row_when_clean(scheduled_verify_db):
    from tasks import verify_audit_chain

    session = scheduled_verify_db()
    append_audit_log(session, "ALERT_RECEIVED", {"equipment_id": "EQ-1"})
    append_audit_log(session, "TELEMETRY_ACCEPTED", {"equipment_id": "EQ-1", "alert_created": False})
    session.commit()
    before_count = session.query(AuditLog).count()
    session.close()

    result = verify_audit_chain.run()

    assert result["chain_integrity"] is True
    assert result["checked_events"] == before_count

    session = scheduled_verify_db()
    after_count = session.query(AuditLog).count()
    session.close()
    # A clean run must not append anything -- only a real mismatch does.
    assert after_count == before_count


def test_scheduled_verify_detects_a_tampered_audit_row_and_writes_a_failure_record(scheduled_verify_db):
    from tasks import verify_audit_chain

    session = scheduled_verify_db()
    append_audit_log(session, "ALERT_RECEIVED", {"equipment_id": "EQ-1"})
    session.commit()

    tampered = session.query(AuditLog).order_by(AuditLog.id.asc()).first()
    tampered.payload = '{"equipment_id": "HACKED"}'
    session.commit()
    session.close()

    result = verify_audit_chain.run()

    assert result["chain_integrity"] is False

    session = scheduled_verify_db()
    failures = session.query(AuditLog).filter(AuditLog.event_name == "AUDIT_CHAIN_INTEGRITY_FAILURE").all()
    session.close()
    assert len(failures) == 1


def test_scheduled_verify_detects_a_tampered_lifecycle_row(scheduled_verify_db):
    from tasks import verify_audit_chain

    session = scheduled_verify_db()
    session.add(WorkOrderRecord(id="WO-1", equipment_id="EQ-1", technician_id="T-1", part_number="P-1"))
    session.flush()
    append_lifecycle_event(session, work_order_id="WO-1", to_status="PENDING_APPROVAL", actor_id="sys", actor_role="internal")
    append_lifecycle_event(
        session, work_order_id="WO-1", to_status="APPROVED", from_status="PENDING_APPROVAL",
        actor_id="eng-1", actor_role="engineer",
    )
    session.commit()

    second = session.query(WorkOrderLifecycleEvent).order_by(WorkOrderLifecycleEvent.id.desc()).first()
    second.note = "rewritten after the fact"
    session.commit()
    session.close()

    result = verify_audit_chain.run()

    assert result["chain_integrity"] is False
    assert result["checked_events"] == 1  # only the first, untampered row verifies clean


def test_verify_audit_chain_is_registered_on_the_beat_schedule():
    from tasks import celery_app

    entry = celery_app.conf.beat_schedule.get("verify-audit-chain")
    assert entry is not None
    assert entry["task"] == "tasks.verify_audit_chain"
