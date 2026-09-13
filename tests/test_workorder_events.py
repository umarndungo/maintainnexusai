"""Regression test: creating a work order must publish a live SSE event.

Previously ``POST /maintenance/work-orders`` (the path the ETL pipeline uses
to dispatch a work order from a scored alert) wrote its lifecycle event
directly and never called ``publish_event`` — only the later manual
approve/reject/escalate actions did (via ``_transition``). So a connected
dashboard never saw the pipeline's own dispatch happen live; only a human
review action afterward produced a push.
"""

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base


@pytest.fixture
def workorders_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr("api.workorders.SessionLocal", session_factory)
    return session_factory


def test_create_work_order_publishes_a_live_event(monkeypatch, workorders_db):
    from api.workorders import WorkOrderCreate, create_work_order

    published = []
    monkeypatch.setattr("api.workorders.publish_event", published.append)

    payload = WorkOrderCreate(equipment_id="PUMP-1", technician_id="TECH-1", part_number="PART-1")
    response = asyncio.run(create_work_order(payload))

    assert len(published) == 1
    event = published[0]
    assert event["type"] == "work_order.lifecycle"
    assert event["work_order_id"] == response["work_order_id"]
    assert event["equipment_id"] == "PUMP-1"
    assert event["to_status"] == "PENDING_APPROVAL"
