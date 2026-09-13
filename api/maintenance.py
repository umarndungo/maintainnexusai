"""
Maintenance Alerts Module — Gateway for Equipment Failure Events.

This module accepts both direct maintenance alerts and raw equipment
telemetry. Raw telemetry is treated as the first input to the system and
is validated before any risk scoring or alert creation takes place.

High-risk telemetry is converted into an alert payload and forwarded to a
Celery task queue for asynchronous ETL pipeline execution.
"""

import json
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from database.auditing import append_audit_log
from database.db import SessionLocal
from database.models import AuditLog
from api.auth import require_internal_or_user
from etl.ge_validation import validate_telemetry_data
from etl.metrics import alerts_ingested

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/alerts",
    tags=["Alerts"],
    dependencies=[Depends(require_internal_or_user)],
)


def _write_audit_log(event_name: str, payload: dict):
    db = SessionLocal()
    try:
        append_audit_log(db, event_name, payload)
        db.commit()
    finally:
        db.close()


class AlertPayload(BaseModel):
    """
    Schema for an incoming maintenance alert from equipment.

    Attributes
    ----------
    equipment_id : str
        Unique identifier of the affected machine / asset.
    part_number  : str
        The part that triggered the alert (e.g. "Pump Seal Kit #A4").
    severity     : str
        Alert severity level — one of "HIGH", "CRITICAL", "MEDIUM".
    failure_code : str
        Machine-readable error code (e.g. "ERR_SEAL_LEAK").
    risk_probability : float | None
        Model probability that the asset will fail within the next 48 hours.
    telemetry : dict | None
        The telemetry snapshot that triggered this alert.
    triggered_by_model : bool | None
        Indicates whether alert creation was driven by the model.
    model_version : str | None
        Optional model version identifier.
    """
    equipment_id: str
    part_number: str
    severity: str
    failure_code: str
    risk_probability: float | None = None
    telemetry: dict | None = None
    triggered_by_model: bool | None = None
    model_version: str | None = None


@router.post("/maintenance", status_code=status.HTTP_202_ACCEPTED)
async def receive_alert(alert: AlertPayload):
    """
    Accept a maintenance alert and enqueue it for async processing.

    The alert is *accepted* (HTTP 202) rather than *completed* (HTTP 200)
    because actual processing is delegated to the Celery task queue which
    runs the ETL pipeline asynchronously.

    Returns
    -------
    dict
        - status   : "queued" — acknowledging receipt
        - task_id  : UUID string for tracing this alert through the system
        - data     : the validated alert payload
    """
    task_id = str(uuid.uuid4())
    alert_dict = alert.model_dump()
    persisted_payload = {**alert_dict, "task_id": task_id}

    # Track ingestion
    alerts_ingested.inc()

    # Store the task_id with the alert payload for later retrieval.
    db = SessionLocal()
    try:
        append_audit_log(db, "ALERT_RECEIVED", persisted_payload)
        db.commit()
    finally:
        db.close()

    # Enqueue to Celery (fire-and-forget) with the full payload including task_id.
    try:
        from tasks import process_alert
        process_alert.delay(persisted_payload)
        logger.info("Alert %s enqueued to Celery.", task_id)
    except Exception as exc:
        # If Celery is unreachable, log but still return 202 —
        # the sensor should not block on a transient broker issue.
        logger.error("Failed to enqueue alert %s: %s", task_id, exc)

    return {
        "status": "queued",
        "task_id": task_id,
        "data": alert_dict,
        "model_context": {
            "risk_probability": alert_dict.get("risk_probability"),
            "triggered_by_model": alert_dict.get("triggered_by_model"),
            "model_version": alert_dict.get("model_version"),
        },
    }


class TelemetryPayload(BaseModel):
    """Raw telemetry accepted from sensors/UI. Only the legacy fields are
    required so existing callers keep working; the richer sensor readings
    below are optional and, when a caller doesn't have them, are filled in
    with neutral defaults by ``etl.telemetry.enrich_for_scoring`` before ML
    scoring (see that module for exactly what's inferred vs. defaulted)."""

    model_config = ConfigDict(extra="allow")

    equipment_id: str
    temperature: float
    vibration: float
    installation_age_hours: int
    timestamp: str
    asset_id: str | None = None
    asset_type: str | None = None
    operating_state: str | None = None
    alarm_code: str | None = None
    pressure_bar: float | None = None
    flow_rate_m3h: float | None = None
    motor_current_a: float | None = None
    valve_position_pct: float | None = None


@router.post("/telemetry", status_code=status.HTTP_202_ACCEPTED)
async def receive_telemetry(telemetry: TelemetryPayload):
    """Validate and enqueue raw telemetry; Celery performs risk scoring."""
    telemetry_dict = telemetry.model_dump()
    if not validate_telemetry_data(telemetry_dict):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "rejected",
                "reason": "Telemetry payload failed validation",
            },
        )

    task_id = str(uuid.uuid4())
    telemetry_dict["task_id"] = task_id
    _write_audit_log("TELEMETRY_RECEIVED", telemetry_dict)

    try:
        from tasks import process_telemetry

        process_telemetry.delay(telemetry_dict)
        logger.info("Telemetry %s enqueued to Celery.", task_id)
    except Exception as exc:
        logger.error("Failed to enqueue telemetry %s: %s", task_id, exc)

    return {
        "status": "queued",
        "task_id": task_id,
        "data": telemetry_dict,
    }


@router.get("/recent", status_code=status.HTTP_200_OK)
async def list_recent_alerts():
    """
    Return recent alerts that were received by the pipeline.

    Alerts are reconstructed from ``AuditLog`` entries created when the
    system accepted and queued the maintenance alert.
    """
    db = SessionLocal()
    try:
        records = (
            db.query(AuditLog)
            .filter(AuditLog.event_name == "ALERT_RECEIVED")
            .order_by(AuditLog.timestamp.desc())
            .all()
        )

        alerts = []
        for record in records:
            try:
                payload = json.loads(record.payload)
            except json.JSONDecodeError:
                continue

            alerts.append(
                {
                    "task_id": payload.get("task_id"),
                    "equipment_id": payload.get("equipment_id"),
                    "part_number": payload.get("part_number"),
                    "severity": payload.get("severity"),
                    "failure_code": payload.get("failure_code"),
                    "risk_probability": payload.get("risk_probability"),
                    "triggered_by_model": payload.get("triggered_by_model"),
                    "model_version": payload.get("model_version"),
                    "received_at": record.timestamp.isoformat(),
                }
            )

        return alerts
    finally:
        db.close()
