"""
Equipment Monitoring Module — Live equipment readings for the web UI.

Every telemetry reading Celery scores (see ``tasks._telemetry_check_payload``)
is written to the append-only ``AuditLog`` as a ``TELEMETRY_CHECK`` event, so
this module reconstructs "what does equipment monitoring look like right
now" by reading that log rather than needing a dedicated telemetry table.

Endpoints
---------
``GET /api/v1/monitoring/equipment``
    The latest reading for every piece of equipment that has reported.
``GET /api/v1/monitoring/equipment/{equipment_id}/history``
    The full recorded reading history for one piece of equipment.
"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, status

from api.auth import require_roles
from database.db import SessionLocal
from database.models import AuditLog
from etl.telemetry import ALERT_CREATION_THRESHOLD
from ml.scoring import METADATA

router = APIRouter(
    prefix="/api/v1/monitoring",
    tags=["Monitoring"],
    dependencies=[Depends(require_roles("engineer", "supervisor"))],
)

# The model's own validation-tuned threshold (~0.12) — below this, a reading
# is NORMAL; at or above it (but below the alert-creation gate), it's
# APPROACHING_THRESHOLD. See ALERT_CREATION_THRESHOLD's docstring in
# etl.telemetry for why these are two different numbers.
WARNING_THRESHOLD = float(METADATA["threshold"])
PREDICTION_HORIZON_HOURS = 6

# How many TELEMETRY_CHECK rows to scan. AuditLog.payload is a JSON string
# column (no per-equipment index), so filtering happens in Python after a
# bounded scan — fine at this app's demo/hackathon scale, but the first
# thing to revisit if the audit log grows large enough for this to matter.
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
        "source": "audit_log+model_metadata",
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


def _reading_from_row(record: AuditLog) -> dict | None:
    """Turn one TELEMETRY_CHECK audit row into an EquipmentReading, or
    ``None`` if the row doesn't carry a usable telemetry payload."""
    try:
        payload = json.loads(record.payload)
    except json.JSONDecodeError:
        return None

    telemetry = payload.get("telemetry") or {}
    equipment_id = payload.get("equipment_id") or telemetry.get("equipment_id")
    if not equipment_id:
        return None

    risk_probability = payload.get("risk_probability")
    prediction = None
    if risk_probability is not None:
        risk_probability = float(risk_probability)
        prediction = {
            "failure_probability": round(risk_probability, 4),
            "failure_predicted": risk_probability >= ALERT_CREATION_THRESHOLD,
            "risk_level": payload.get("risk_level") or payload.get("health_status") or "LOW",
            "threshold": ALERT_CREATION_THRESHOLD,
            "prediction_horizon_hours": payload.get("prediction_horizon_hours", PREDICTION_HORIZON_HOURS),
        }

    state = _state_for(risk_probability)
    return {
        "id": record.id,
        "equipment_id": equipment_id,
        "station_id": payload.get("station_id") or telemetry.get("station_id"),
        "telemetry": telemetry,
        "prediction": prediction,
        "state": state,
        "evaluation_reason": _EVALUATION_REASONS[state],
        "received_at": record.timestamp.isoformat(),
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
            db.query(AuditLog)
            .filter(AuditLog.event_name == "TELEMETRY_CHECK")
            .order_by(AuditLog.timestamp.desc())
            .limit(SCAN_LIMIT)
            .all()
        )
    finally:
        db.close()

    latest_by_equipment: dict[str, dict] = {}
    for record in rows:  # newest first — keep only the first (latest) row seen per equipment
        reading = _reading_from_row(record)
        if reading is None or reading["equipment_id"] in latest_by_equipment:
            continue
        if not _accessible(reading, user):
            continue
        latest_by_equipment[reading["equipment_id"]] = reading

    equipment = sorted(latest_by_equipment.values(), key=lambda reading: reading["equipment_id"])
    return {"equipment": equipment, "thresholds": _thresholds(), "source": "audit_log"}


@router.get("/equipment/{equipment_id}/history", status_code=status.HTTP_200_OK)
async def equipment_history(
    equipment_id: str,
    user: Annotated[dict, Depends(require_roles("engineer", "supervisor"))],
):
    """Return recorded readings for one piece of equipment, oldest first."""
    db = SessionLocal()
    try:
        rows = (
            db.query(AuditLog)
            .filter(AuditLog.event_name == "TELEMETRY_CHECK")
            .order_by(AuditLog.timestamp.desc())
            .limit(SCAN_LIMIT)
            .all()
        )
    finally:
        db.close()

    readings = []
    for record in reversed(rows):  # oldest -> newest, matching the frontend trend chart's expectation
        reading = _reading_from_row(record)
        if reading is None or reading["equipment_id"] != equipment_id:
            continue
        if not _accessible(reading, user):
            continue
        readings.append(reading)

    return {"readings": readings[-EQUIPMENT_HISTORY_LIMIT:], "thresholds": _thresholds()}
