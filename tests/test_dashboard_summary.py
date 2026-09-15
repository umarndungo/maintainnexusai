"""Regression test: /dashboard/summary must report real downtime.

Previously ``downtime_minutes`` (and the ``mean_repair_time_minutes`` /
``uptime_percentage`` derived from it) were computed from a work-order
status/age heuristic instead of the actual ``DowntimeWindow`` rows the
lifecycle pipeline records — the same rows ``/dashboard/executive-summary``
and ``/dashboard/equipment/{id}/downtime`` already use correctly. This test
seeds real downtime windows and asserts the summary reflects their exact
elapsed time, not a bucketed guess.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, DowntimeWindow, WorkOrderRecord


@pytest.fixture
def dashboard_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr("api.dashboard.SessionLocal", session_factory)
    return session_factory


def _supervisor():
    """get_dashboard_summary now takes the caller's user for station
    scoping (see api.dashboard._accessible_equipment_ids) — a supervisor
    is unscoped, so these downtime-focused tests keep seeing everything,
    same as before that parameter existed."""
    return {"id": "supervisor-demo", "role": "supervisor", "station_ids": []}


def _seed_work_order(session, work_order_id: str, equipment_id: str, created_at: datetime):
    session.add(
        WorkOrderRecord(
            id=work_order_id,
            equipment_id=equipment_id,
            technician_id="TECH-1",
            part_number="PART-1",
            created_at=created_at,
        )
    )


def test_summary_downtime_matches_real_downtime_windows(dashboard_db):
    from api.dashboard import get_dashboard_summary

    now = datetime.now(timezone.utc)
    session = dashboard_db()
    _seed_work_order(session, "WO-1", "PUMP-1", now - timedelta(hours=2))
    # A closed 45-minute window, well inside the endpoint's 24h "recent" cutoff.
    session.add(
        DowntimeWindow(
            equipment_id="PUMP-1",
            work_order_id="WO-1",
            started_at=now - timedelta(minutes=90),
            ended_at=now - timedelta(minutes=45),
        )
    )
    session.commit()
    session.close()

    result = asyncio.run(get_dashboard_summary(_supervisor()))

    assert result["downtime_minutes"] == pytest.approx(45.0, abs=0.1)
    assert result["mean_repair_time_minutes"] == pytest.approx(45.0, abs=0.1)


def test_summary_counts_open_downtime_window_up_to_now(dashboard_db):
    from api.dashboard import get_dashboard_summary

    now = datetime.now(timezone.utc)
    session = dashboard_db()
    _seed_work_order(session, "WO-2", "PUMP-2", now - timedelta(hours=1))
    # Still open (ended_at is None) — must count as ongoing downtime up to now.
    session.add(
        DowntimeWindow(
            equipment_id="PUMP-2",
            work_order_id="WO-2",
            started_at=now - timedelta(minutes=30),
            ended_at=None,
        )
    )
    session.commit()
    session.close()

    result = asyncio.run(get_dashboard_summary(_supervisor()))

    assert result["downtime_minutes"] == pytest.approx(30.0, abs=0.5)


def test_summary_reports_zero_downtime_with_no_windows(dashboard_db):
    from api.dashboard import get_dashboard_summary

    result = asyncio.run(get_dashboard_summary(_supervisor()))

    assert result["downtime_minutes"] == 0.0
    assert result["mean_repair_time_minutes"] == 0.0
    assert result["uptime_percentage"] == 99.9


def test_summary_ignores_downtime_windows_outside_the_recent_cutoff(dashboard_db):
    """A window that started days ago must not inflate today's figure."""
    from api.dashboard import get_dashboard_summary

    now = datetime.now(timezone.utc)
    session = dashboard_db()
    _seed_work_order(session, "WO-3", "PUMP-3", now - timedelta(days=5))
    session.add(
        DowntimeWindow(
            equipment_id="PUMP-3",
            work_order_id="WO-3",
            started_at=now - timedelta(days=5),
            ended_at=now - timedelta(days=5) + timedelta(hours=3),
        )
    )
    session.commit()
    session.close()

    result = asyncio.run(get_dashboard_summary(_supervisor()))

    assert result["downtime_minutes"] == 0.0
