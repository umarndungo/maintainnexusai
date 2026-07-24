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
import logging

import requests

logger = logging.getLogger(__name__)

# Base URL — configurable so the Celery worker can reach the web_api container.
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


def dispatch_work_order(payload: dict):
    """
    Submit a work-order creation request to the API.

    Calls ``POST /api/v1/maintenance/work-orders`` with the assembled
    payload. The downstream API is responsible for persisting the created
    work order to PostgreSQL and returning the resulting record.

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

    if res.status_code == 409:
        logger.error(
            "Duplicate work order detected: API returned 409 for payload %s."
            " This likely means the work order was already created upstream.",
            payload,
        )
        return None

    if res.status_code != 201:
        logger.error("Work-order API returned %s — %s", res.status_code, res.text)
        return None

    return res.json()
