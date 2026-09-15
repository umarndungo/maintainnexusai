"""Tests for the two Part B work-order gaps in api/workorders.py:

- ``PATCH /work-orders/{id}/start`` (DISPATCHED -> IN_PROGRESS) — previously
  the SMS-reply path (api/notifications.py) was the only way to reach this
  status; this adds the direct HTTP action through the same
  advance_work_order_status() writer.
- ``PATCH /work-orders/{id}/assign`` — reassign technician_id, validated
  against the roster (api/technicians.py) and recorded in the general
  audit_logs hash chain rather than as a lifecycle-status transition.
"""

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.auditing import append_audit_log
from database.lifecycle import append_lifecycle_event
from database.models import AuditLog, Base, WorkOrderRecord


@pytest.fixture
def workorders_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr("api.workorders.SessionLocal", session_factory)
    return session_factory


def _engineer():
    return {"id": "engineer-demo", "role": "engineer", "station_ids": ["STATION-1"]}


def _technician():
    return {"id": "TECH-101", "role": "technician", "station_ids": []}


def _seed_dispatched(session, work_order_id="WO-1", equipment_id="PUMP-1", technician_id="TECH-101"):
    session.add(
        WorkOrderRecord(id=work_order_id, equipment_id=equipment_id, technician_id=technician_id, part_number="PART-1")
    )
    session.flush()
    append_lifecycle_event(session, work_order_id=work_order_id, to_status="PENDING_APPROVAL", actor_id="sys", actor_role="internal")
    append_lifecycle_event(
        session, work_order_id=work_order_id, from_status="PENDING_APPROVAL", to_status="APPROVED",
        actor_id="eng-1", actor_role="engineer",
    )
    append_lifecycle_event(
        session, work_order_id=work_order_id, from_status="APPROVED", to_status="DISPATCHED",
        actor_id="eng-1", actor_role="engineer",
    )
    session.commit()


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

def test_start_transitions_dispatched_to_in_progress(monkeypatch, workorders_db):
    from api.workorders import start_work_order

    monkeypatch.setattr("api.workorders.publish_event", lambda event: None)

    session = workorders_db()
    _seed_dispatched(session)
    session.close()

    result = asyncio.run(start_work_order("WO-1", _technician()))

    assert result["status"] == "IN_PROGRESS"
    assert result["work_order_id"] == "WO-1"


def test_start_rejects_a_work_order_that_is_not_yet_dispatched(monkeypatch, workorders_db):
    from fastapi import HTTPException

    from api.workorders import start_work_order

    session = workorders_db()
    session.add(WorkOrderRecord(id="WO-2", equipment_id="PUMP-2", technician_id="TECH-101", part_number="PART-1"))
    session.flush()
    append_lifecycle_event(session, work_order_id="WO-2", to_status="PENDING_APPROVAL", actor_id="sys", actor_role="internal")
    session.commit()
    session.close()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(start_work_order("WO-2", _technician()))
    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# /assign
# ---------------------------------------------------------------------------

def test_assign_reassigns_technician_and_appends_an_audit_log_row(monkeypatch, workorders_db):
    from api.workorders import WorkOrderAssign, assign_work_order

    published = []
    monkeypatch.setattr("api.workorders.publish_event", published.append)

    session = workorders_db()
    _seed_dispatched(session, technician_id="TECH-102")  # off-shift, but that's fine as the *current* assignee
    session.close()

    result = asyncio.run(assign_work_order("WO-1", WorkOrderAssign(technician_id="TECH-101"), _engineer()))

    assert result["technician_id"] == "TECH-101"
    assert result["status"] == "DISPATCHED"  # unaffected -- reassignment isn't a status transition

    session = workorders_db()
    record = session.query(WorkOrderRecord).filter(WorkOrderRecord.id == "WO-1").first()
    assert record.technician_id == "TECH-101"
    audit_rows = session.query(AuditLog).filter(AuditLog.event_name == "WORK_ORDER_REASSIGNED").all()
    session.close()
    assert len(audit_rows) == 1

    assert len(published) == 1
    assert published[0]["type"] == "work_order.reassigned"
    assert published[0]["technician_id"] == "TECH-101"


def test_assign_rejects_an_unknown_technician_id(monkeypatch, workorders_db):
    from fastapi import HTTPException

    from api.workorders import WorkOrderAssign, assign_work_order

    session = workorders_db()
    _seed_dispatched(session)
    session.close()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(assign_work_order("WO-1", WorkOrderAssign(technician_id="TECH-999"), _engineer()))
    assert exc_info.value.status_code == 404


def test_assign_rejects_an_off_shift_technician(monkeypatch, workorders_db):
    from fastapi import HTTPException

    from api.workorders import WorkOrderAssign, assign_work_order

    session = workorders_db()
    _seed_dispatched(session)  # currently TECH-101
    session.close()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(assign_work_order("WO-1", WorkOrderAssign(technician_id="TECH-102"), _engineer()))  # off-shift
    assert exc_info.value.status_code == 409


def test_assign_rejects_reassigning_to_the_same_technician(monkeypatch, workorders_db):
    from fastapi import HTTPException

    from api.workorders import WorkOrderAssign, assign_work_order

    session = workorders_db()
    _seed_dispatched(session)  # currently TECH-101
    session.close()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(assign_work_order("WO-1", WorkOrderAssign(technician_id="TECH-101"), _engineer()))
    assert exc_info.value.status_code == 409
