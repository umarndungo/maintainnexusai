"""
Celery Task Definitions — Async Alert Processing & Scheduled Pipeline Runs.

Architecture
------------
- ``celery_app``: the shared Celery instance (broker=Redis).
- ``process_alert``: the task invoked by the FastAPI gateway when a new
  maintenance alert arrives. It runs the full ETL pipeline asynchronously
  so the HTTP request returns immediately (HTTP 202).
- ``scheduled_pipeline``: a periodic task registered via Celery Beat that
  simulates a cron-like processing of a sample alert (every 5 minutes).

Integration Contract
--------------------
- The FastAPI gateway calls ``process_alert.delay(alert_dict)``.
- The worker runs inside the ``celery_worker`` container.
- The beat scheduler runs inside the ``celery_beat`` container.
"""

import json
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone

from celery import Celery, signals
from celery.schedules import crontab

from api.equipment import EQUIPMENT_IDS, PARTS
from database.auditing import append_audit_log
from database.db import SessionLocal
from database.lifecycle import append_lifecycle_event, current_work_order_status
from database.models import WorkOrderRecord
from etl.extract import get_technician, resolve_cert_for_failure
from etl.telemetry import generate_telemetry
from etl.ml_client import predict_risk
from config import CELERY_BROKER_URL

# ---------------------------------------------------------------------------
# Celery app — single point of truth for the whole system
# ---------------------------------------------------------------------------
BROKER_URL = CELERY_BROKER_URL

celery_app = Celery("maintainnexus", broker=BROKER_URL, backend=BROKER_URL)

# Default settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)

# ---------------------------------------------------------------------------
# Celery Beat schedule — periodic pipeline run every 5 minutes
# ---------------------------------------------------------------------------

celery_app.conf.beat_schedule = {
    "pipeline-every-5-minutes": {
        "task": "tasks.scheduled_pipeline_run",
        "schedule": crontab(minute="*/5"),
    },
    "escalate-stale-approvals": {
        "task": "tasks.escalate_stale_approvals",
        "schedule": crontab(minute="*/5"),
    },
}

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signal: ensure database schema is current when the worker starts
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Helper: write an AuditLog row
# ---------------------------------------------------------------------------
def _write_audit_log(event_name: str, payload: dict):
    """Insert an append-only audit entry into PostgreSQL."""
    db = SessionLocal()
    try:
        append_audit_log(db, event_name, payload)
        db.commit()
    except Exception as exc:
        logger.error("Audit log write failed: %s", exc)
        db.rollback()
    finally:
        db.close()


def _telemetry_check_payload(telemetry: dict, score_result: dict, alert_created: bool) -> dict:
    """Build the audit payload for one scored telemetry reading.

    Written for *every* reading that reaches the model — not just the ones
    that clear the alert threshold — so ``api.monitoring`` can reconstruct
    each equipment's current state and history straight from the audit log
    instead of needing a separate telemetry table. ``health_status`` is kept
    (alongside the clearer ``risk_level``) because ``dashboard.get_dashboard_summary``
    already reads it from this event.
    """
    risk_probability = (
        score_result.get("risk_score", score_result.get("failure_probability", 0.0))
        if isinstance(score_result, dict)
        else float(score_result)
    )
    risk_level = score_result.get("risk_level") if isinstance(score_result, dict) else None
    return {
        "equipment_id": telemetry.get("equipment_id"),
        "station_id": telemetry.get("station_id"),
        "telemetry": telemetry,
        "risk_probability": round(float(risk_probability), 4),
        "risk_level": risk_level,
        "health_status": risk_level,
        "prediction_horizon_hours": score_result.get("prediction_horizon_hours", 6) if isinstance(score_result, dict) else 6,
        "top_features": score_result.get("top_features", []) if isinstance(score_result, dict) else [],
        "model_version": score_result.get("model_version") if isinstance(score_result, dict) else None,
        "alert_created": alert_created,
    }


def _find_existing_work_order_by_task_id(task_id: str) -> dict | None:
    """Return a previously created work order for the given alert task ID."""
    db = SessionLocal()
    try:
        record = (
            db.query(WorkOrderRecord)
            .filter(WorkOrderRecord.alert_task_id == task_id)
            .first()
        )
        if record is None:
            return None

        return {
            "work_order_id": record.id,
            "equipment_id": record.equipment_id,
            "assigned_technician_id": record.technician_id,
            "reserved_part": record.part_number,
            "status": current_work_order_status(db, record.id),
            "created_at": record.created_at.isoformat(),
            "alert_task_id": record.alert_task_id,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task: process a single maintenance alert
# ---------------------------------------------------------------------------
@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_alert(self, alert: dict):
    """
    Execute the full ETL pipeline for one alert.

    Called asynchronously from the FastAPI gateway.  Retries up to 3 times
    with a 30-second delay if the pipeline fails.
    """
    from etl.pipeline import process_alert_pipeline

    logger.info("Processing alert %s", alert.get("task_id", "N/A"))

    task_id = alert.get("task_id")
    if task_id is not None:
        existing_work_order = _find_existing_work_order_by_task_id(task_id)
        if existing_work_order is not None:
            logger.info(
                "Duplicate alert %s detected; returning existing work order %s",
                task_id,
                existing_work_order["work_order_id"],
            )
            _write_audit_log(
                "DUPLICATE_ALERT_SKIPPED",
                {
                    "task_id": task_id,
                    "existing_work_order_id": existing_work_order["work_order_id"],
                },
            )
            return existing_work_order

    # Audit: alert processing started
    _write_audit_log("ALERT_PROCESSING", alert)

    try:
        result = process_alert_pipeline(alert)
    except Exception as exc:
        logger.exception("Pipeline failed for alert %s", task_id or "N/A")
        _write_audit_log("PIPELINE_FAILED", {"alert": alert, "error": str(exc)})
        raise self.retry(exc=exc)

    if result and result.get("work_order_id"):
        logger.info("Work order created: %s", result["work_order_id"])
        _write_audit_log("WORK_ORDER_CREATED", result)
        return result

    if result and result.get("status") == "external_source":
        logger.info(
            "Pipeline completed with external source handling: %s",
            result.get("reason"),
        )
        _write_audit_log(
            "EXTERNAL_SOURCE_REQUIRED",
            {
                "alert": alert,
                "status": result.get("status"),
                "reason": result.get("reason"),
                "required_cert": result.get("required_cert"),
            },
        )
        return result

    logger.warning("Pipeline returned no work order — check upstream services.")
    _write_audit_log("PIPELINE_HOLD", {"alert": alert, "result": result})
    return None


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_telemetry(self, telemetry: dict):
    """Score validated telemetry in Celery and enqueue qualifying alerts."""
    from etl.telemetry import score_and_decide

    task_id = telemetry.get("task_id")
    logger.info("Scoring telemetry %s in Celery.", task_id or "N/A")
    try:
        score_result, alert_payload = score_and_decide(telemetry)
    except Exception as exc:
        logger.exception("Risk scoring failed for telemetry %s", task_id or "N/A")
        _write_audit_log("RISK_SCORING_FAILED", {"telemetry": telemetry, "error": str(exc)})
        raise self.retry(exc=exc)

    if score_result is not None:
        _write_audit_log(
            "TELEMETRY_CHECK",
            _telemetry_check_payload(telemetry, score_result, alert_created=alert_payload is not None),
        )

    if alert_payload is None:
        _write_audit_log("TELEMETRY_ACCEPTED", {"telemetry": telemetry, "alert_created": False})
        return {"status": "accepted", "alert_created": False, "task_id": task_id}

    alert_payload["task_id"] = task_id or alert_payload["task_id"]
    alert_payload["received_at"] = datetime.now(timezone.utc).isoformat()
    _write_audit_log("ALERT_RECEIVED", alert_payload)
    process_alert.delay(alert_payload)
    return {"status": "queued", "alert_created": True, "task_id": alert_payload["task_id"]}


# ---------------------------------------------------------------------------
# Task: periodic pipeline run (Celery Beat)
# ---------------------------------------------------------------------------
@celery_app.task
def escalate_stale_approvals():
    """Append ESCALATED for approvals that have exceeded the two-hour SLA."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    db = SessionLocal()
    try:
        records = db.query(WorkOrderRecord).all()
        escalated = 0
        for record in records:
            if record.created_at is None or record.created_at > cutoff:
                continue
            if current_work_order_status(db, record.id) != "PENDING_APPROVAL":
                continue
            append_lifecycle_event(
                db,
                work_order_id=record.id,
                from_status="PENDING_APPROVAL",
                to_status="ESCALATED",
                actor_id="scheduler",
                actor_role="internal",
                note="Approval exceeded two-hour SLA",
            )
            escalated += 1
        db.commit()
        if escalated:
            _write_audit_log("WORK_ORDERS_ESCALATED", {"count": escalated})
        return escalated
    finally:
        db.close()


@celery_app.task
def scheduled_pipeline_run():
    """
    Cron-like job: generate telemetry, score it, and emit a maintenance alert
    only when predicted failure risk exceeds the configured threshold.
    """
    from etl.telemetry import score_and_decide

    telemetry = generate_telemetry()
    score_result, alert_payload = score_and_decide(telemetry)

    if score_result is not None:
        _write_audit_log(
            "TELEMETRY_CHECK",
            _telemetry_check_payload(telemetry, score_result, alert_created=alert_payload is not None),
        )

    if alert_payload is None:
        logger.info(
            "Telemetry did not meet the alert creation criteria for %s.",
            telemetry["equipment_id"],
        )
        _write_audit_log("TELEMETRY_ACCEPTED", {"telemetry": telemetry, "alert_created": False})
        return

    logger.info("High-risk telemetry detected, dispatching alert: %s", alert_payload)
    _write_audit_log("TELEMETRY_RECEIVED", telemetry)
    _write_audit_log("ALERT_RECEIVED", alert_payload)

    required_cert = resolve_cert_for_failure(alert_payload["failure_code"])
    tech = get_technician(required_cert)
    if tech is None:
        logger.info(
            "No on-shift technician currently holds %s certification; sending alert for external handling.",
            required_cert,
        )

    process_alert.delay(alert_payload)
