"""
Dashboard Summary Module — Aggregated backend data for the UI.

Provides a single endpoint that returns work order counts, alert counts,
available on-shift technicians, and current inventory levels.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, status
from api.auth import require_roles

from api.equipment import INVENTORY_DB
from api.technicians import TECHNICIANS
from database.auditing import GENESIS_HASH, compute_audit_hash
from database.db import SessionLocal
from database.lifecycle import compute_lifecycle_hash, current_work_order_status
from database.models import AuditLog, DowntimeWindow, WorkOrderLifecycleEvent, WorkOrderRecord
from api.auth import get_current_user

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(require_roles("technician", "engineer", "executive", "supervisor"))],
)


def _normalize_timestamp(dt: datetime) -> datetime:
    if dt is None:
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get("/summary", status_code=status.HTTP_200_OK)
async def get_dashboard_summary():
    """
    Return aggregated dashboard data for the Flutter UI.

    Returns
    -------
    dict
        - work_order_count      : total dispatched work orders
        - alert_count           : total received alert events
        - available_technicians : currently on-shift technician roster
        - inventory             : current part availability for the warehouse
        - backend_status        : health of the dashboard backend aggregation endpoint
    """
    db = SessionLocal()
    try:
        work_order_count = db.query(WorkOrderRecord).count()
        alert_count = (
            db.query(AuditLog)
            .filter(AuditLog.event_name == "ALERT_RECEIVED")
            .count()
        )

        now = datetime.now(timezone.utc)
        recent_window = now - timedelta(hours=24)
        recent_alert_rows = (
            db.query(AuditLog)
            .filter(
                AuditLog.event_name == "ALERT_RECEIVED",
                AuditLog.timestamp >= recent_window,
            )
            .order_by(AuditLog.timestamp.desc())
            .all()
        )

        incident_equipment_ids = set()
        for record in recent_alert_rows:
            try:
                payload = json.loads(record.payload)
                incident_equipment_ids.add(payload.get("equipment_id"))
            except json.JSONDecodeError:
                continue

        incident_count = len(incident_equipment_ids)

        recent_work_orders = (
            db.query(WorkOrderRecord)
            .filter(WorkOrderRecord.created_at >= recent_window)
            .all()
        )
        current_statuses = {
            record.id: current_work_order_status(db, record.id)
            for record in recent_work_orders
        }
        open_work_orders = sum(
            status != "COMPLETED" for status in current_statuses.values()
        )

        external_source_alerts = (
            db.query(AuditLog)
            .filter(AuditLog.event_name == "EXTERNAL_SOURCE_REQUIRED")
            .count()
        )

        health_checks = []
        health_check_rows = (
            db.query(AuditLog)
            .filter(AuditLog.event_name == "TELEMETRY_CHECK")
            .order_by(AuditLog.timestamp.desc())
            .limit(5)
            .all()
        )
        for record in health_check_rows:
            try:
                payload = json.loads(record.payload)
            except json.JSONDecodeError:
                continue

            telemetry = payload.get("telemetry", {})
            health_checks.append(
                {
                    "equipment_id": telemetry.get("equipment_id"),
                    "temperature": telemetry.get("temperature"),
                    "vibration": telemetry.get("vibration"),
                    "installation_age_hours": telemetry.get("installation_age_hours"),
                    "risk_probability": payload.get("risk_probability"),
                    "health_status": payload.get("health_status"),
                    "checked_at": record.timestamp.isoformat(),
                }
            )

        # Real downtime, from the same DowntimeWindow rows opened/closed by
        # work-order lifecycle transitions (see database/lifecycle.py) —
        # not a status/age heuristic. Matches the window /executive-summary
        # already uses, scoped to the same recent_window as the rest of
        # this endpoint's "recent" figures.
        recent_downtime_windows = (
            db.query(DowntimeWindow)
            .filter(DowntimeWindow.started_at >= recent_window)
            .all()
        )
        now = datetime.now(timezone.utc)
        downtime_minutes = sum(
            (
                (_normalize_timestamp(window.ended_at) or now)
                - _normalize_timestamp(window.started_at)
            ).total_seconds()
            / 60.0
            for window in recent_downtime_windows
        )

        mean_repair_time_minutes = (
            round(downtime_minutes / len(recent_downtime_windows), 1)
            if recent_downtime_windows
            else 0.0
        )
        uptime_percentage = round(
            max(85.0, min(99.9, 100.0 - (downtime_minutes / 1440.0 * 100.0))),
            1,
        )
    finally:
        db.close()

    technicians = [
        {
            "id": tech["id"],
            "name": tech["name"],
            "certs": tech["certs"],
        }
        for tech in TECHNICIANS
        if tech["on_shift"]
    ]

    inventory = [
        {
            "part_number": part,
            "quantity_available": qty,
            "in_stock": qty > 0,
        }
        for part, qty in INVENTORY_DB.items()
    ]

    return {
        "work_order_count": work_order_count,
        "alert_count": alert_count,
        "available_technicians": technicians,
        "inventory": inventory,
        "incident_count": incident_count,
        "open_work_orders": open_work_orders,
        "downtime_minutes": round(downtime_minutes, 1),
        "mean_repair_time_minutes": mean_repair_time_minutes,
        "uptime_percentage": uptime_percentage,
        "external_source_alerts": external_source_alerts,
        "recent_health_checks": health_checks,
        "backend_status": "ok",
    }


@router.get("/audit-logs", status_code=status.HTTP_200_OK)
async def get_audit_logs():
    """Return recent audit log entries for the UI insights screen."""
    db = SessionLocal()
    try:
        records = (
            db.query(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "id": record.id,
                "event_name": record.event_name,
                "payload": record.payload,
                "timestamp": record.timestamp.isoformat(),
            }
            for record in records
        ]
    finally:
        db.close()


def _verify_chain(rows, compute_hash) -> tuple[bool, int]:
    """Walk one hash chain from genesis, recomputing each row's hash from
    its actual stored data. Stops at the first mismatch (a tampered row, a
    reordered/deleted row, or a break in the previous_event_hash link) and
    reports how many rows verified clean before that point."""
    previous_hash = GENESIS_HASH
    checked = 0
    for row in rows:
        if not row.event_hash or row.previous_event_hash != previous_hash:
            return False, checked
        if compute_hash(row, previous_hash) != row.event_hash:
            return False, checked
        previous_hash = row.event_hash
        checked += 1
    return True, checked


@router.get("/audit-logs/verify")
async def verify_audit_chain():
    """Recompute both append-only hash chains from genesis and report
    whether every row's event_hash still matches its data. This is what
    actually establishes integrity — a successful /audit-logs read only
    means the rows loaded, not that they're untampered.
    """
    db = SessionLocal()
    try:
        audit_rows = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
        lifecycle_rows = (
            db.query(WorkOrderLifecycleEvent)
            .order_by(WorkOrderLifecycleEvent.id.asc())
            .all()
        )
        audit_ok, audit_checked = _verify_chain(audit_rows, compute_audit_hash)
        lifecycle_ok, lifecycle_checked = _verify_chain(lifecycle_rows, compute_lifecycle_hash)
        return {
            "chain_integrity": audit_ok and lifecycle_ok,
            "checked_events": audit_checked + lifecycle_checked,
            "chain": "audit_logs+work_order_lifecycle_events",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        db.close()


@router.get("/equipment/{equipment_id}/downtime")
async def equipment_downtime(equipment_id: str):
    db = SessionLocal()
    try:
        windows = db.query(DowntimeWindow).filter(
            DowntimeWindow.equipment_id == equipment_id
        ).order_by(DowntimeWindow.started_at.desc()).all()
        now = datetime.now(timezone.utc)
        return [{
            "id": window.id,
            "work_order_id": window.work_order_id,
            "started_at": window.started_at.isoformat(),
            "ended_at": window.ended_at.isoformat() if window.ended_at else None,
            "duration_seconds": int(((window.ended_at or now) - window.started_at).total_seconds()),
            "cause_alert_id": window.cause_alert_id,
        } for window in windows]
    finally:
        db.close()


@router.get("/executive-summary")
async def executive_summary(user: Annotated[dict, Depends(get_current_user)]):
    if user["role"] not in {"executive", "supervisor"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Executive or supervisor role required")
    db = SessionLocal()
    try:
        windows = db.query(DowntimeWindow).all()
        now = datetime.now(timezone.utc)
        downtime_seconds = sum(
            ((window.ended_at or now) - window.started_at).total_seconds()
            for window in windows
        )
        completed = sum(window.ended_at is not None for window in windows)
        return {
            "downtime_minutes": round(downtime_seconds / 60, 1),
            "downtime_windows": len(windows),
            "completed_windows": completed,
            "open_windows": len(windows) - completed,
            "uptime_trend": "stable" if downtime_seconds < 1440 * 60 else "at_risk",
        }
    finally:
        db.close()
