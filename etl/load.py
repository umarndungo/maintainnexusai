"""
Data Loading Module — Downstream API Persistence & DB Recording.

Dispatches a fully-formed work-order payload to the work-orders API for
persistence and execution. This is the "L" in the ETL pipeline — the
final step that commits the transformed data into the operational system.

After the API call succeeds, the work-order ID is also persisted to the
local PostgreSQL ``work_orders`` table so the system has an authoritative
record independent of the API's in-memory store.
"""

import os
import json
import logging
from datetime import datetime, timezone

import requests

from database.db import SessionLocal
from database.models import WorkOrderRecord

logger = logging.getLogger(__name__)

# Base URL — configurable so the Celery worker can reach the web_api container.
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


def dispatch_work_order(payload: dict):
    """
    Submit a work-order creation request to the API and persist to DB.

    Calls ``POST /api/v1/maintenance/work-orders`` with the assembled
    payload. On success (HTTP 201) the returned work-order ID is also
    inserted into the local PostgreSQL ``work_orders`` table.

    Parameters
    ----------
    payload : dict
        Work-order dictionary as produced by ``transform.build_work_order_payload``.
        Must contain ``equipment_id``, ``technician_id``, ``part_number``,
        and ``status``.

    Returns
    -------
    dict or None
        The API response JSON (containing the assigned ``work_order_id``)
        on success, or ``None`` if the upstream rejected the request.
    """
    # Post to the API
    res = requests.post(f"{BASE_URL}/maintenance/work-orders", json=payload)

    if res.status_code != 201:
        logger.error("Work-order API returned %s — %s", res.status_code, res.text)
        return None

    result = res.json()
    wo_id = result.get("work_order_id")

    # Persist to PostgreSQL
    if wo_id:
        _persist_work_order(wo_id, payload)

    return result


def _persist_work_order(wo_id: str, payload: dict):
    """
    Insert a work-order record into the local PostgreSQL database.

    This runs inside the same process (API or Celery worker) and is
    independent of the upstream API's mock in-memory store.
    """
    db = SessionLocal()
    try:
        record = WorkOrderRecord(
            id=wo_id,
            equipment_id=payload.get("equipment_id", ""),
            technician_id=payload.get("technician_id", ""),
            part_number=payload.get("part_number", ""),
            status=payload.get("status", "CREATED"),
            created_at=datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()
        logger.info("Work order %s persisted to database.", wo_id)
    except Exception as exc:
        logger.error("Failed to persist work order %s: %s", wo_id, exc)
        db.rollback()
    finally:
        db.close()
