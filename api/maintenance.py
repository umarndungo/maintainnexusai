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

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database.db import SessionLocal
from database.models import AuditLog
from etl.ge_validation import validate_telemetry_data
from etl.metrics import alerts_ingested
from etl.telemetry import process_raw_telemetry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


def _write_audit_log(event_name: str, payload: dict):
    db = SessionLocal()
    try:
        db.add(
            AuditLog(
                event_name=event_name,
                payload=json.dumps(payload),
                timestamp=datetime.now(timezone.utc),
            )
        )
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
        db.add(
            AuditLog(
                event_name="ALERT_RECEIVED",
                payload=json.dumps(persisted_payload),
                timestamp=datetime.now(timezone.utc),
            )
        )
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
    equipment_id: str
    temperature: float
    vibration: float
    installation_age_hours: int
    timestamp: str


@router.post("/telemetry", status_code=status.HTTP_202_ACCEPTED)
async def receive_telemetry(telemetry: TelemetryPayload):
    """Accept raw telemetry and create an alert only when it qualifies."""
    telemetry_dict = telemetry.model_dump()
    if not validate_telemetry_data(telemetry_dict):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "rejected",
                "reason": "Telemetry payload failed validation",
            },
        )

    alert_payload = process_raw_telemetry(telemetry_dict)
    if alert_payload is None:
        _write_audit_log("TELEMETRY_ACCEPTED", telemetry_dict)
        return {
            "status": "accepted",
            "alert_created": False,
            "message": "Telemetry validated but did not exceed alert threshold.",
        }

    alerts_ingested.inc()
    alert_payload["received_at"] = datetime.now(timezone.utc).isoformat()
    _write_audit_log("ALERT_RECEIVED", alert_payload)

    try:
        from tasks import process_alert

        process_alert.delay(alert_payload)
        logger.info("Alert %s enqueued to Celery from telemetry.", alert_payload["task_id"])
    except Exception as exc:
        logger.error("Failed to enqueue alert %s: %s", alert_payload["task_id"], exc)

    return {
        "status": "queued",
        "task_id": alert_payload["task_id"],
        "data": alert_payload,
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
