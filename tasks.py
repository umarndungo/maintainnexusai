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

import os
import json
import logging
import random
import uuid
from datetime import datetime, timezone

from celery import Celery, signals

from api.equipment import EQUIPMENT_IDS, PARTS
from database.db import SessionLocal
from database.init_db import init_database
from database.models import Base, WorkOrderRecord, AuditLog
from etl.extract import get_technician, resolve_cert_for_failure
from etl.telemetry import build_alert_from_telemetry, generate_telemetry
from ml.scoring import score_telemetry

# ---------------------------------------------------------------------------
# Celery app — single point of truth for the whole system
# ---------------------------------------------------------------------------
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

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
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "pipeline-every-5-minutes": {
        "task": "tasks.scheduled_pipeline_run",
        "schedule": crontab(minute="*/5"),
    },
}

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signal: create tables when the worker starts (only once)
# ---------------------------------------------------------------------------
@signals.worker_ready.connect
def create_tables_on_startup(**kwargs):
    """Ensure DB tables exist and schema is up to date when the Celery worker boots."""
    init_database()
    logger.info("Database tables verified / created.")


# ---------------------------------------------------------------------------
# Helper: write an AuditLog row
# ---------------------------------------------------------------------------
def _write_audit_log(event_name: str, payload: dict):
    """Insert an append-only audit entry into PostgreSQL."""
    db = SessionLocal()
    try:
        record = AuditLog(
            event_name=event_name,
            payload=json.dumps(payload),
            timestamp=datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()
    except Exception as exc:
        logger.error("Audit log write failed: %s", exc)
        db.rollback()
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

    # Audit: alert processing started
    _write_audit_log("ALERT_PROCESSING", alert)

    try:
        result = process_alert_pipeline(alert)
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
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


# ---------------------------------------------------------------------------
# Task: periodic pipeline run (Celery Beat)
# ---------------------------------------------------------------------------
@celery_app.task
def scheduled_pipeline_run():
    """
    Cron-like job: generate telemetry, score it, and emit a maintenance alert
    only when predicted failure risk exceeds the configured threshold.
    """
    telemetry = generate_telemetry()
    risk_probability = score_telemetry(telemetry)
    health_status = "CRITICAL" if risk_probability > 0.85 else "NORMAL"

    _write_audit_log(
        "TELEMETRY_CHECK",
        {
            "telemetry": telemetry,
            "risk_probability": risk_probability,
            "health_status": health_status,
            "timestamp": telemetry["timestamp"],
        },
    )

    logger.info("Telemetry generated for %s with risk %.3f", telemetry["equipment_id"], risk_probability)

    if risk_probability > 0.85:
        alert_payload = build_alert_from_telemetry(
            telemetry=telemetry,
            risk_probability=risk_probability,
            model_version="mock-v1",
        )
        alert_payload["task_id"] = str(uuid.uuid4())
        _write_audit_log("ALERT_RECEIVED", alert_payload)

        required_cert = resolve_cert_for_failure(alert_payload["failure_code"])
        tech = get_technician(required_cert)
        if tech is None:
            logger.info(
                "No on-shift technician currently holds %s certification; sending alert for external handling.",
                required_cert,
            )
        else:
            logger.info("High-risk telemetry detected, dispatching alert: %s", alert_payload)

        process_alert.delay(alert_payload)
    else:
        logger.info(
            "Telemetry is healthy; no alert generated for %s.",
            telemetry["equipment_id"],
        )
