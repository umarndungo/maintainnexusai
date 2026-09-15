"""Tests for the Predict -> Decide -> Act decision engine
(etl/decision_engine.py's policy gate + api/operations.py's Act step).
"""

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Decision, LoadingPoint, LoadingSlot, OperationalAction


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr("api.operations.SessionLocal", session_factory)
    return session_factory


def _engineer():
    return {"id": "engineer-demo", "role": "engineer", "station_ids": []}


# ---------------------------------------------------------------------------
# should_evaluate — pure policy gate, no DB
# ---------------------------------------------------------------------------

def test_should_evaluate_policy_thresholds():
    from etl.decision_engine import should_evaluate

    assert should_evaluate("MEDIUM") is True   # default criticality is CRITICAL -> threshold MEDIUM
    assert should_evaluate("LOW") is False
    assert should_evaluate(None) is False
    assert should_evaluate("HIGH", criticality="LOW") is False
    assert should_evaluate("CRITICAL", criticality="LOW") is True


# ---------------------------------------------------------------------------
# The Act step — api.operations.reassign_loading_point
# ---------------------------------------------------------------------------

def test_qualifying_risk_applies_a_reassignment(db):
    from api.operations import ReassignmentRequest, reassign_loading_point

    result = asyncio.run(reassign_loading_point(
        ReassignmentRequest(equipment_id="PUMP-101", asset_type="PUMP", risk_level="HIGH", reading_id=7)
    ))

    assert result["status"] == "applied"
    assert result["original_bay"] == "BAY-PUMP-101"
    assert result["new_bay"] == "BAY-ALT-PUMP-101"

    session = db()
    original = session.query(LoadingPoint).filter(LoadingPoint.bay_code == "BAY-PUMP-101").first()
    alternate = session.query(LoadingPoint).filter(LoadingPoint.bay_code == "BAY-ALT-PUMP-101").first()
    assert original.capacity_status == "UNAVAILABLE"
    assert alternate.capacity_status == "AVAILABLE"
    decision = session.query(Decision).filter(Decision.id == result["decision_id"]).first()
    assert decision.affected_equipment_id == "PUMP-101"
    assert decision.requires_human_approval is False
    assert decision.reading_id == 7
    session.close()


def test_below_threshold_risk_makes_no_db_writes(db):
    from api.operations import ReassignmentRequest, reassign_loading_point

    result = asyncio.run(reassign_loading_point(
        ReassignmentRequest(equipment_id="PUMP-101", asset_type="PUMP", risk_level="LOW", reading_id=1)
    ))

    assert result["status"] == "not_evaluated"
    session = db()
    assert session.query(LoadingPoint).count() == 0
    session.close()


def test_repeat_call_after_the_bay_is_already_unavailable_does_not_spawn_a_new_truck(db):
    """A second, later qualifying reading for the same equipment must
    recognize the bay is already pulled from service — not schedule and
    reassign a phantom new truck there."""
    from api.operations import ReassignmentRequest, reassign_loading_point

    first = asyncio.run(reassign_loading_point(
        ReassignmentRequest(equipment_id="PUMP-101", asset_type="PUMP", risk_level="HIGH", reading_id=1)
    ))
    second = asyncio.run(reassign_loading_point(
        ReassignmentRequest(equipment_id="PUMP-101", asset_type="PUMP", risk_level="HIGH", reading_id=2)
    ))

    assert first["status"] == "applied"
    assert second["status"] == "already_unavailable"
    assert second["decision_id"] == first["decision_id"]

    session = db()
    assert session.query(OperationalAction).count() == 1
    assert session.query(Decision).count() == 1
    session.close()


def test_matching_idempotency_key_on_an_already_available_bay_is_not_reapplied(db):
    """Defensive branch for a genuine race (two concurrent requests both
    reading the bay as AVAILABLE before either commits): if an
    OperationalAction already exists for this equipment+truck, don't
    apply a second one even if the bay row hasn't flipped yet."""
    session = db()
    bay = LoadingPoint(bay_code="BAY-PUMP-101", equipment_id="PUMP-101", capacity_status="AVAILABLE")
    session.add(bay)
    session.flush()
    slot = LoadingSlot(
        loading_point_id=bay.id,
        truck_code="TRUCK-RACE01",
        scheduled_arrival=datetime.now(timezone.utc),
        status="SCHEDULED",
    )
    session.add(slot)
    session.flush()
    decision = Decision(decision_type="REASSIGN_LOADING_POINT", reason="race", affected_equipment_id="PUMP-101")
    session.add(decision)
    session.flush()
    session.add(OperationalAction(
        decision_id=decision.id,
        action_type="REASSIGN_LOADING_POINT",
        truck_code="TRUCK-RACE01",
        idempotency_key="PUMP-101:TRUCK-RACE01",
        status="APPLIED",
    ))
    session.commit()
    session.close()

    from api.operations import ReassignmentRequest, reassign_loading_point

    result = asyncio.run(reassign_loading_point(
        ReassignmentRequest(equipment_id="PUMP-101", asset_type="PUMP", risk_level="HIGH", reading_id=2)
    ))

    assert result["status"] == "already_applied"
    session = db()
    assert session.query(OperationalAction).count() == 1
    session.close()


def test_no_alternate_capacity_skips_reassignment_without_writing_a_decision(db):
    from api.operations import ReassignmentRequest, reassign_loading_point

    session = db()
    session.add(LoadingPoint(bay_code="BAY-PUMP-101", equipment_id="PUMP-101", capacity_status="AVAILABLE"))
    session.add(LoadingPoint(bay_code="BAY-ALT-PUMP-101", capacity_status="UNAVAILABLE"))  # no spare capacity
    session.commit()
    session.close()

    result = asyncio.run(reassign_loading_point(
        ReassignmentRequest(equipment_id="PUMP-101", asset_type="PUMP", risk_level="HIGH", reading_id=1)
    ))

    assert result["status"] == "no_capacity"
    session = db()
    assert session.query(Decision).count() == 0
    assert session.query(OperationalAction).count() == 0
    session.close()


def test_list_and_get_decision_round_trip(db):
    from api.operations import ReassignmentRequest, get_decision, list_decisions, reassign_loading_point

    applied = asyncio.run(reassign_loading_point(
        ReassignmentRequest(equipment_id="VALVE-201", asset_type="VALVE", risk_level="CRITICAL", reading_id=9)
    ))

    listing = asyncio.run(list_decisions(_engineer()))
    assert len(listing["decisions"]) == 1
    assert listing["decisions"][0]["id"] == applied["decision_id"]

    detail = asyncio.run(get_decision(applied["decision_id"], _engineer()))
    assert detail["action"]["status"] == "APPLIED"
    assert detail["outcome"]["action_success"] is True


def test_get_unknown_decision_is_404(db):
    from fastapi import HTTPException

    from api.operations import get_decision

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_decision(999, _engineer()))
    assert exc_info.value.status_code == 404
