"""
Maintenance Alerts Module — Gateway for Equipment Failure Events.

Acts as the ingestion gateway for real-time maintenance alerts emitted
by industrial equipment. Each alert is acknowledged immediately with a
unique task ID (fire-and-forget pattern) so the calling sensor/PLC does
not block on downstream processing.

The alert is forwarded to a Celery task queue for asynchronous ETL
pipeline execution.
"""

import json
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, status
from pydantic import BaseModel

from database.db import SessionLocal
from database.models import AuditLog
from etl.metrics import alerts_ingested

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


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
    """
    equipment_id: str
    part_number: str
    severity: str
    failure_code: str


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
                    "received_at": record.timestamp.isoformat(),
                }
            )

        return alerts
    finally:
        db.close()
