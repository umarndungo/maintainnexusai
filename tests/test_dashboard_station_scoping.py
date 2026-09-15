"""Tests for station-scoping on GET /dashboard/summary and
GET /dashboard/audit-logs (api/dashboard.py).

Both endpoints were previously global regardless of the caller's role —
a station-scoped engineer/technician saw every station's work orders and
alerts, unlike api.monitoring's equipment-list endpoint, which already
scopes by the caller's station_ids (api.monitoring._accessible). This
folds the same rule into the dashboard: visible if the equipment's latest
reading has no recorded station_id (today's demo telemetry rarely sets
one), or if it matches one of the caller's own station_ids.
"""

import asyncio
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.auditing import append_audit_log
from database.models import AuditLog, Base, EquipmentReading, WorkOrderRecord


@pytest.fixture
def dashboard_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr("api.dashboard.SessionLocal", session_factory)
    return session_factory


def _supervisor():
    return {"id": "supervisor-demo", "role": "supervisor", "station_ids": []}


def _engineer(station_ids):
    return {"id": "engineer-demo", "role": "engineer", "station_ids": station_ids}


def _seed_reading(session, equipment_id, station_id):
    session.add(
        EquipmentReading(
            equipment_id=equipment_id,
            asset_type="PUMP",
            station_id=station_id,
            telemetry="{}",
        )
    )


def test_supervisor_sees_every_station_unscoped(dashboard_db):
    from api.dashboard import get_dashboard_summary

    session = dashboard_db()
    _seed_reading(session, "PUMP-1", "STATION-1")
    _seed_reading(session, "PUMP-2", "STATION-2")
    session.add(WorkOrderRecord(id="WO-1", equipment_id="PUMP-1", technician_id="T-1", part_number="P-1"))
    session.add(WorkOrderRecord(id="WO-2", equipment_id="PUMP-2", technician_id="T-1", part_number="P-1"))
    session.commit()
    session.close()

    result = asyncio.run(get_dashboard_summary(_supervisor()))

    assert result["work_order_count"] == 2


def test_station_scoped_engineer_sees_only_their_station(dashboard_db):
    from api.dashboard import get_dashboard_summary

    session = dashboard_db()
    _seed_reading(session, "PUMP-1", "STATION-1")
    _seed_reading(session, "PUMP-2", "STATION-2")
    session.add(WorkOrderRecord(id="WO-1", equipment_id="PUMP-1", technician_id="T-1", part_number="P-1"))
    session.add(WorkOrderRecord(id="WO-2", equipment_id="PUMP-2", technician_id="T-1", part_number="P-1"))
    session.commit()
    session.close()

    result = asyncio.run(get_dashboard_summary(_engineer(["STATION-1"])))

    assert result["work_order_count"] == 1


def test_station_scoped_engineer_still_sees_equipment_with_no_recorded_station(dashboard_db):
    """Today's demo telemetry rarely sets station_id at all -- hiding
    those readings from a station-scoped user would leave their
    dashboard empty, same reasoning as api.monitoring._accessible."""
    from api.dashboard import get_dashboard_summary

    session = dashboard_db()
    _seed_reading(session, "PUMP-1", "STATION-1")
    _seed_reading(session, "PUMP-3", None)
    session.add(WorkOrderRecord(id="WO-1", equipment_id="PUMP-1", technician_id="T-1", part_number="P-1"))
    session.add(WorkOrderRecord(id="WO-3", equipment_id="PUMP-3", technician_id="T-1", part_number="P-1"))
    session.commit()
    session.close()

    result = asyncio.run(get_dashboard_summary(_engineer(["STATION-1"])))

    assert result["work_order_count"] == 2


def test_audit_logs_are_station_scoped_by_the_equipment_they_concern(dashboard_db):
    from api.dashboard import get_audit_logs

    session = dashboard_db()
    _seed_reading(session, "PUMP-1", "STATION-1")
    _seed_reading(session, "PUMP-2", "STATION-2")
    append_audit_log(session, "ALERT_RECEIVED", {"equipment_id": "PUMP-1"})
    append_audit_log(session, "ALERT_RECEIVED", {"equipment_id": "PUMP-2"})
    session.commit()
    session.close()

    result = asyncio.run(get_audit_logs(_engineer(["STATION-1"])))

    equipment_ids = {json.loads(r["payload"]).get("equipment_id") for r in result}
    assert equipment_ids == {"PUMP-1"}


def test_audit_logs_with_no_identifiable_equipment_stay_visible_to_everyone(dashboard_db):
    """A row that carries no equipment_id in any recognised shape (see
    api.dashboard._audit_log_equipment_id) has no station to scope by --
    it must not silently vanish for a station-scoped caller."""
    from api.dashboard import get_audit_logs

    session = dashboard_db()
    _seed_reading(session, "PUMP-1", "STATION-1")
    append_audit_log(session, "SMS_PROMPTS_EXPIRED", {"count": 2})
    session.commit()
    session.close()

    result = asyncio.run(get_audit_logs(_engineer(["STATION-9"])))

    assert any(r["event_name"] == "SMS_PROMPTS_EXPIRED" for r in result)
