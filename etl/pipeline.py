"""
ETL Pipeline Orchestrator — End-to-End Alert Processing Flow.

This module ties the four ETL phases (Validate → Extract → Transform → Load)
into a single, callable workflow. Each phase can short-circuit with an
early return (and a diagnostic message) if a prerequisite is not met,
preventing wasted downstream calls.

Typical usage::

    from etl.pipeline import process_alert_pipeline

    alert = {
        "equipment_id": "PUMP-901",
        "part_number": "Pump Seal Kit #A4",
        "severity": "HIGH",
        "failure_code": "ERR_SEAL_LEAK",
    }
    result = process_alert_pipeline(alert)
"""

import time
import logging

from etl.extract import check_stock, get_technician, resolve_cert_for_failure
from etl.validate import validate_alert_data
from etl.transform import build_work_order_payload
from etl.load import dispatch_work_order
from etl.metrics import (
    pipeline_duration,
    pipeline_results,
    phase_duration,
    stock_out_events,
    no_technician_events,
)

logger = logging.getLogger(__name__)


def process_alert_pipeline(alert: dict):
    """
    Execute the complete ETL workflow for a single maintenance alert.

    Steps
    -----
    1. **Validate** — reject malformed or incomplete alerts early.
    2. **Extract stock** — verify the replacement part is available.
    3. **Extract technician** — find an on-shift certified technician.
    4. **Transform** — combine alert + technician into a work-order payload.
    5. **Load** — dispatch the work order to the operational system.

    Parameters
    ----------
    alert : dict
        Raw alert payload from the maintenance gateway. Must contain at
        minimum ``equipment_id``, ``part_number``, and ``severity`` keys.

    Returns
    -------
    dict or None
        The work-order creation response on success, or ``None`` if any
        stage of the pipeline failed.
    """
    t_start = time.perf_counter()

    try:
        # ---------- Phase 1: Validate ----------
        t0 = time.perf_counter()
        if not validate_alert_data(alert):
            logger.warning(
                "Validation Failed for alert %s: Invalid Alert Format",
                alert.get("task_id", "N/A"),
            )
            phase_duration.labels(phase="validate").observe(time.perf_counter() - t0)
            pipeline_results.labels(status="failure").inc()
            return None
        phase_duration.labels(phase="validate").observe(time.perf_counter() - t0)

        # ---------- Phase 2: Check part stock ----------
        t0 = time.perf_counter()
        stock_info = check_stock(alert["part_number"])
        if not stock_info or not stock_info.get("in_stock"):
            part = alert["part_number"]
            logger.warning("Hold: Part %s unavailable.", part)
            stock_out_events.labels(part_number=part).inc()
            phase_duration.labels(phase="check_stock").observe(time.perf_counter() - t0)
            pipeline_results.labels(status="hold").inc()
            return None
        phase_duration.labels(phase="check_stock").observe(time.perf_counter() - t0)

        # ---------- Phase 3: Find certified technician ----------
        t0 = time.perf_counter()
        required_cert = resolve_cert_for_failure(alert.get("failure_code", ""))
        tech = get_technician(required_cert)
        if not tech:
            logger.info(
                "No certified technician on shift for %s; continuing as external alert.",
                required_cert,
            )
            no_technician_events.inc()
            phase_duration.labels(phase="get_technician").observe(time.perf_counter() - t0)
            pipeline_results.labels(status="external_source").inc()
            return {
                "status": "external_source",
                "reason": f"No certified technician on shift (need {required_cert})",
                "required_cert": required_cert,
            }
        phase_duration.labels(phase="get_technician").observe(time.perf_counter() - t0)

        # ---------- Phase 4: Transform into work-order ----------
        t0 = time.perf_counter()
        wo_payload = build_work_order_payload(alert, tech)
        phase_duration.labels(phase="transform").observe(time.perf_counter() - t0)

        # ---------- Phase 5: Load / dispatch ----------
        t0 = time.perf_counter()
        result = dispatch_work_order(wo_payload)
        phase_duration.labels(phase="dispatch").observe(time.perf_counter() - t0)

        # Record overall duration and outcome
        pipeline_duration.observe(time.perf_counter() - t_start)

        if result and result.get("work_order_id"):
            pipeline_results.labels(status="success").inc()
            return result

        pipeline_results.labels(status="failure").inc()
        return None

    except Exception as exc:
        logger.exception(
            "Unhandled pipeline exception for alert %s",
            alert.get("task_id", "N/A"),
        )
        pipeline_results.labels(status="failure").inc()
        return None
