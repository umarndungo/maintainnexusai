"""Regression tests for the three 02-BACKEND-GUIDE.md §3 / 00-PROJECT-DOC.md
§8 gaps: duplicate alert_task_id wasn't rejected, and the recent-alerts
list didn't dedupe by task_id. (The third item, database/scheduler.py,
was dead code — deleting it has no runtime behavior to test.)
"""

import asyncio
import json

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.auditing import append_audit_log
from database.models import AuditLog, Base, WorkOrderRecord


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr("api.workorders.SessionLocal", session_factory)
    monkeypatch.setattr("api.maintenance.SessionLocal", session_factory)
    return session_factory


def test_duplicate_alert_task_id_is_rejected_with_409(db, monkeypatch):
    from api.workorders import WorkOrderCreate, create_work_order

    # publish_event touches a module-level dict keyed by station_id/"*";
    # harmless in tests but not the thing under test — leave it be.
    first = asyncio.run(create_work_order(
        WorkOrderCreate(equipment_id="PUMP-901", technician_id="TECH-101", part_number="Seal", alert_task_id="alert-1")
    ))
    assert first["work_order_id"]

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(create_work_order(
            WorkOrderCreate(equipment_id="PUMP-901", technician_id="TECH-101", part_number="Seal", alert_task_id="alert-1")
        ))
    assert exc_info.value.status_code == 409
    assert first["work_order_id"] in exc_info.value.detail

    session = db()
    assert session.query(WorkOrderRecord).filter(WorkOrderRecord.alert_task_id == "alert-1").count() == 1
    session.close()


def test_work_orders_without_alert_task_id_are_never_blocked(db):
    """Manually-created work orders (no upstream alert) have no
    alert_task_id to dedupe on — the guard must not false-positive on
    None == None."""
    from api.workorders import WorkOrderCreate, create_work_order

    first = asyncio.run(create_work_order(WorkOrderCreate(equipment_id="PUMP-901", technician_id="TECH-101", part_number="Seal")))
    second = asyncio.run(create_work_order(WorkOrderCreate(equipment_id="PUMP-902", technician_id="TECH-102", part_number="Seal")))
    assert first["work_order_id"] != second["work_order_id"]


def test_recent_alerts_dedupes_by_task_id_keeping_the_newest(db):
    from api.maintenance import list_recent_alerts

    session = db()
    append_audit_log(session, "ALERT_RECEIVED", {"task_id": "dup-1", "equipment_id": "PUMP-901", "severity": "HIGH"})
    append_audit_log(session, "ALERT_RECEIVED", {"task_id": "other", "equipment_id": "VALVE-201", "severity": "LOW"})
    # A retried Celery task re-emitting the same alert — same task_id.
    append_audit_log(session, "ALERT_RECEIVED", {"task_id": "dup-1", "equipment_id": "PUMP-901", "severity": "CRITICAL"})
    session.commit()
    session.close()

    alerts = asyncio.run(list_recent_alerts())

    dup_alerts = [a for a in alerts if a["task_id"] == "dup-1"]
    assert len(dup_alerts) == 1
    assert dup_alerts[0]["severity"] == "CRITICAL"  # the newer of the two rows
    assert len(alerts) == 2  # dup-1 (once) + other


def test_recent_alerts_keeps_every_row_with_no_task_id(db):
    """Nothing to dedupe against — must not collapse distinct alerts
    that simply never got a task_id."""
    from api.maintenance import list_recent_alerts

    session = db()
    append_audit_log(session, "ALERT_RECEIVED", {"equipment_id": "PUMP-901", "severity": "HIGH"})
    append_audit_log(session, "ALERT_RECEIVED", {"equipment_id": "VALVE-201", "severity": "LOW"})
    session.commit()
    session.close()

    alerts = asyncio.run(list_recent_alerts())
    assert len(alerts) == 2
