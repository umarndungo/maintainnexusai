"""
Equipment Monitoring Module — Live equipment readings for the web UI.

Reads from ``EquipmentReading`` — the table the telemetry ETL's Load
step (etl/telemetry_pipeline.py) writes to *before* ML scoring runs,
then updates in place once a score comes back (etl/readings_client.py).
This is the single structured source of "what does equipment monitoring
look like right now" — replacing the previous approach of re-parsing
``AuditLog`` JSON rows on every request.

Endpoints
---------
``GET /api/v1/monitoring/equipment``
    The latest reading for every piece of equipment that has reported.
``GET /api/v1/monitoring/equipment/{equipment_id}/history``
    The full recorded reading history for one piece of equipment.
``POST /api/v1/monitoring/readings`` (internal-only)
    ETL Load step: persist one validated/transformed reading, unscored.
``PATCH /api/v1/monitoring/readings/{id}`` (internal-only)
    Attach an ML score to an already-loaded reading.
"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.auth import require_internal_service, require_roles
from database.db import SessionLocal
from database.models import EquipmentReading
from etl.telemetry import ALERT_CREATION_THRESHOLD
from ml.scoring import METADATA

router = APIRouter(
    prefix="/api/v1/monitoring",
    tags=["Monitoring"],
    dependencies=[Depends(require_roles("engineer", "supervisor"))],
)

# Separate router for the ETL Load/score-update calls — internal-service
# gated like /ml/predict-risk, not human-role gated like the router above.
internal_router = APIRouter(
    prefix="/api/v1/monitoring",
    tags=["Monitoring"],
    dependencies=[Depends(require_internal_service)],
)

# The model's own validation-tuned threshold (~0.12) — below this, a reading
# is NORMAL; at or above it (but below the alert-creation gate), it's
# APPROACHING_THRESHOLD. See ALERT_CREATION_THRESHOLD's docstring in
# etl.telemetry for why these are two different numbers.
WARNING_THRESHOLD = float(METADATA["threshold"])
PREDICTION_HORIZON_HOURS = 6

# How many rows list_equipment scans to find the latest per equipment_id.
# Now backed by an index (equipment_id, received_at) rather than a raw
# JSON-string table scan, but still a bounded read rather than an
# unbounded one — fine at this app's demo/hackathon scale.
SCAN_LIMIT = 2000
EQUIPMENT_HISTORY_LIMIT = 200

_EVALUATION_REASONS = {
    "FAILURE_DETECTED": "Predicted failure risk has crossed the alert threshold; a maintenance alert has been raised.",
    "APPROACHING_THRESHOLD": "Predicted failure risk is elevated but has not reached the alert threshold.",
    "NORMAL": "Predicted failure risk is within normal operating range.",
    "UNSCORED": "This reading has not been scored by the model yet.",
}


def _thresholds() -> dict:
    return {
        "failure_probability": ALERT_CREATION_THRESHOLD,
        "warning_probability": WARNING_THRESHOLD,
        "prediction_horizon_hours": PREDICTION_HORIZON_HOURS,
        "source": "equipment_readings+model_metadata",
        "sensor_limits": None,
    }


def _state_for(risk_probability: float | None) -> str:
    if risk_probability is None:
        return "UNSCORED"
    if risk_probability >= ALERT_CREATION_THRESHOLD:
        return "FAILURE_DETECTED"
    if risk_probability >= WARNING_THRESHOLD:
        return "APPROACHING_THRESHOLD"
    return "NORMAL"


def _reading_from_row(record: EquipmentReading) -> dict:
    """Turn one EquipmentReading row into the API's reading shape —
    same field names the frontend already consumed when this was
    reconstructed from audit_log JSON, so the response contract doesn't
    change even though the source table did."""
    try:
        telemetry = json.loads(record.telemetry) if record.telemetry else {}
    except json.JSONDecodeError:
        telemetry = {}

    risk_probability = record.risk_probability
    prediction = None
    if risk_probability is not None:
        prediction = {
            "failure_probability": round(risk_probability, 4),
            "failure_predicted": risk_probability >= ALERT_CREATION_THRESHOLD,
            "risk_level": record.risk_level or "LOW",
            "threshold": ALERT_CREATION_THRESHOLD,
            "prediction_horizon_hours": PREDICTION_HORIZON_HOURS,
        }

    state = _state_for(risk_probability)
    return {
        "id": record.id,
        "equipment_id": record.equipment_id,
        "station_id": record.station_id,
        "telemetry": telemetry,
        "prediction": prediction,
        "state": state,
        "evaluation_reason": _EVALUATION_REASONS[state],
        "received_at": record.received_at.isoformat(),
    }


def _accessible(reading: dict, user: dict) -> bool:
    """Supervisors see every station. A station-scoped user (engineer,
    technician) sees their own stations' equipment plus any reading that
    doesn't carry a station_id at all — telemetry today rarely sets one
    (see etl.telemetry.generate_telemetry), so treating "unknown station"
    as hidden would leave the monitoring workspace empty for everyone."""
    if user["role"] == "supervisor":
        return True
    station_id = reading.get("station_id")
    if station_id is None:
        return True
    return station_id in (user.get("station_ids") or [])


@router.get("/equipment", status_code=status.HTTP_200_OK)
async def list_equipment(user: Annotated[dict, Depends(require_roles("engineer", "supervisor"))]):
    """Return the most recent reading for each accessible piece of equipment."""
    db = SessionLocal()
    try:
        rows = (
            db.query(EquipmentReading)
            .order_by(EquipmentReading.received_at.desc())
            .limit(SCAN_LIMIT)
            .all()
        )
    finally:
        db.close()

    latest_by_equipment: dict[str, dict] = {}
    for record in rows:  # newest first — keep only the first (latest) row seen per equipment
        if record.equipment_id in latest_by_equipment:
            continue
        reading = _reading_from_row(record)
        if not _accessible(reading, user):
            continue
        latest_by_equipment[reading["equipment_id"]] = reading

    equipment = sorted(latest_by_equipment.values(), key=lambda reading: reading["equipment_id"])
    return {"equipment": equipment, "thresholds": _thresholds(), "source": "equipment_readings"}


@router.get("/equipment/{equipment_id}/history", status_code=status.HTTP_200_OK)
async def equipment_history(
    equipment_id: str,
    user: Annotated[dict, Depends(require_roles("engineer", "supervisor"))],
):
    """Return recorded readings for one piece of equipment, oldest first."""
    db = SessionLocal()
    try:
        rows = (
            db.query(EquipmentReading)
            .filter(EquipmentReading.equipment_id == equipment_id)
            .order_by(EquipmentReading.received_at.desc())
            .limit(EQUIPMENT_HISTORY_LIMIT)
            .all()
        )
    finally:
        db.close()

    readings = [_reading_from_row(record) for record in reversed(rows)]  # oldest -> newest
    readings = [r for r in readings if _accessible(r, user)]

    return {"readings": readings, "thresholds": _thresholds()}


# ---------------------------------------------------------------------------
# ETL Load step (called from etl/readings_client.py, before ML scoring)
# ---------------------------------------------------------------------------

class ReadingCreate(BaseModel):
    equipment_id: str
    asset_type: str
    station_id: str | None = None
    telemetry: dict


@internal_router.post("/readings", status_code=status.HTTP_201_CREATED)
async def create_reading(body: ReadingCreate):
    """Persist one validated/transformed reading, unscored — the ETL
    Load step. Called before ML is ever invoked, so the reading survives
    even if scoring subsequently fails."""
    db = SessionLocal()
    try:
        record = EquipmentReading(
            equipment_id=body.equipment_id,
            asset_type=body.asset_type,
            station_id=body.station_id,
            telemetry=json.dumps(body.telemetry),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return {"reading_id": record.id}
    finally:
        db.close()


class ReadingScoreUpdate(BaseModel):
    risk_probability: float
    risk_level: str | None = None
    model_version: str | None = None
    top_features: list[str] = []
    alert_created: bool = False


@internal_router.patch("/readings/{reading_id}", status_code=status.HTTP_200_OK)
async def update_reading_score(reading_id: int, body: ReadingScoreUpdate):
    """Attach an ML score to an already-loaded reading."""
    db = SessionLocal()
    try:
        record = db.query(EquipmentReading).filter(EquipmentReading.id == reading_id).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Reading not found")
        record.risk_probability = body.risk_probability
        record.risk_level = body.risk_level
        record.model_version = body.model_version
        record.top_features = json.dumps(body.top_features)
        record.alert_created = body.alert_created
        db.commit()
        return {"status": "updated", "reading_id": reading_id}
    finally:
        db.close()
