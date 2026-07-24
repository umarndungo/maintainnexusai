"""
Dashboard Summary Module — Aggregated backend data for the UI.

Provides a single endpoint that returns work order counts, alert counts,
available on-shift technicians, and current inventory levels.
"""

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, status

from api.equipment import INVENTORY_DB
from api.technicians import TECHNICIANS
from database.db import SessionLocal
from database.models import AuditLog, WorkOrderRecord

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


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
        open_work_orders = (
            db.query(WorkOrderRecord)
            .filter(WorkOrderRecord.status != "EXECUTED")
            .count()
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

        downtime_minutes = 0.0
        for record in recent_work_orders:
            created_at = _normalize_timestamp(record.created_at)
            age_minutes = max(
                0.0,
                (datetime.now(timezone.utc) - created_at).total_seconds() / 60.0,
            )
            if record.status == "DISPATCHED":
                simulated = 25.0
            elif record.status == "PROCESSING":
                simulated = max(20.0, min(age_minutes, 90.0))
            else:
                simulated = max(30.0, min(age_minutes, 180.0))
            downtime_minutes += simulated

        mean_repair_time_minutes = (
            round(downtime_minutes / len(recent_work_orders), 1)
            if recent_work_orders
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
