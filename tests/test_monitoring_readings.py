"""Tests for api/monitoring.py's EquipmentReading-backed endpoints — the
ETL Load/score-update writes, and the two read endpoints now sourced
from that table instead of parsing audit_log JSON."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, EquipmentReading


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr("api.monitoring.SessionLocal", session_factory)
    return session_factory


def _engineer():
    return {"id": "engineer-demo", "role": "engineer", "station_ids": []}


def test_create_then_update_reading_round_trips(db):
    from api.monitoring import ReadingCreate, ReadingScoreUpdate, create_reading, update_reading_score

    created = asyncio.run(create_reading(ReadingCreate(
        equipment_id="PUMP-142",
        asset_type="PUMP",
        telemetry={"temperature_c": 90.0, "vibration_mm_s": 3.0, "timestamp": "2025-01-01T00:00:00Z"},
    )))
    reading_id = created["reading_id"]

    session = db()
    row = session.query(EquipmentReading).filter(EquipmentReading.id == reading_id).first()
    assert row.equipment_id == "PUMP-142"
    assert row.risk_probability is None  # unscored at Load time — ML hasn't run yet
    session.close()

    result = asyncio.run(update_reading_score(reading_id, ReadingScoreUpdate(
        risk_probability=0.42, risk_level="MEDIUM", model_version="xgboost-1", top_features=["vibration_mm_s"], alert_created=False,
    )))
    assert result["status"] == "updated"

    session = db()
    row = session.query(EquipmentReading).filter(EquipmentReading.id == reading_id).first()
    assert row.risk_probability == 0.42
    assert row.risk_level == "MEDIUM"
    session.close()


def test_update_unknown_reading_id_is_404(db):
    from fastapi import HTTPException

    from api.monitoring import ReadingScoreUpdate, update_reading_score

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(update_reading_score(999, ReadingScoreUpdate(risk_probability=0.1)))
    assert exc_info.value.status_code == 404


def test_list_equipment_returns_latest_reading_per_equipment(db):
    from api.monitoring import list_equipment

    now = datetime.now(timezone.utc)
    session = db()
    session.add(EquipmentReading(equipment_id="PUMP-1", asset_type="PUMP", telemetry="{}", risk_probability=0.1, received_at=now))
    session.add(EquipmentReading(equipment_id="PUMP-1", asset_type="PUMP", telemetry="{}", risk_probability=0.9, received_at=now + timedelta(minutes=5)))  # newer
    session.add(EquipmentReading(equipment_id="VALVE-1", asset_type="VALVE", telemetry="{}", risk_probability=None, received_at=now))
    session.commit()
    session.close()

    result = asyncio.run(list_equipment(_engineer()))

    by_id = {e["equipment_id"]: e for e in result["equipment"]}
    assert len(by_id) == 2
    assert by_id["PUMP-1"]["prediction"]["failure_probability"] == 0.9
    assert by_id["VALVE-1"]["state"] == "UNSCORED"


def test_equipment_history_is_oldest_to_newest_for_one_equipment(db):
    from api.monitoring import equipment_history

    now = datetime.now(timezone.utc)
    session = db()
    session.add(EquipmentReading(equipment_id="PUMP-1", asset_type="PUMP", telemetry="{}", risk_probability=0.1, received_at=now))
    session.add(EquipmentReading(equipment_id="PUMP-1", asset_type="PUMP", telemetry="{}", risk_probability=0.2, received_at=now + timedelta(minutes=5)))
    session.add(EquipmentReading(equipment_id="VALVE-1", asset_type="VALVE", telemetry="{}", risk_probability=0.5, received_at=now))
    session.commit()
    session.close()

    result = asyncio.run(equipment_history("PUMP-1", _engineer()))

    assert [r["prediction"]["failure_probability"] for r in result["readings"]] == [0.1, 0.2]
