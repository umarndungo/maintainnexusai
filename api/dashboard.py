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
from database.models import AuditLog, DowntimeWindow, EquipmentReading, WorkOrderLifecycleEvent, WorkOrderRecord
from api.auth import get_current_user

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(require_roles("technician", "engineer", "executive", "supervisor"))],
)

# How many EquipmentReading rows _accessible_equipment_ids scans to find
# the latest per equipment_id — same bound as api.monitoring.SCAN_LIMIT,
# duplicated rather than imported to keep the two modules independent.
_SCAN_LIMIT = 2000


def _normalize_timestamp(dt: datetime) -> datetime:
    if dt is None:
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _accessible_equipment_ids(db, user: dict) -> set[str] | None:
    """Which equipment_ids this user may see summary/audit data for.

    ``None`` means "no restriction" (supervisor/executive — same
    cross-station roles api.monitoring._accessible already exempts).
    Otherwise: equipment in the user's own stations, plus any equipment
    whose latest reading carries no station_id at all — today's demo
    telemetry (etl.telemetry.generate_telemetry) rarely sets one, so
    treating "unknown station" as hidden would leave a station-scoped
    engineer's dashboard empty. Same rule as api.monitoring._accessible,
    just computed as a set of ids up front rather than per-row.
    """
    if user["role"] in {"supervisor", "executive"}:
        return None
    user_stations = set(user.get("station_ids") or [])
    rows = (
        db.query(EquipmentReading.equipment_id, EquipmentReading.station_id)
        .order_by(EquipmentReading.received_at.desc())
        .limit(_SCAN_LIMIT)
        .all()
    )
    seen: set[str] = set()
    allowed: set[str] = set()
    for equipment_id, station_id in rows:
        if equipment_id in seen:  # only the latest reading per equipment counts
            continue
        seen.add(equipment_id)
        if station_id is None or station_id in user_stations:
            allowed.add(equipment_id)
    return allowed


def _load_payload(record: AuditLog) -> dict:
    """AuditLog.payload is a JSON string; malformed rows degrade to an
    empty dict rather than raising, matching the try/except pattern the
    rest of this endpoint already uses per-row."""
    try:
        return json.loads(record.payload)
    except json.JSONDecodeError:
        return {}


def _audit_log_equipment_id(payload: dict) -> str | None:
    """Best-effort extraction of the equipment_id an audit row concerns —
    payload shapes vary by event_name (see tasks.py/etl.telemetry's
    various _write_audit_log calls), so this checks the handful of shapes
    actually produced rather than assuming one schema."""
    if payload.get("equipment_id"):
        return payload["equipment_id"]
    for nested_key in ("alert", "telemetry"):
        nested = payload.get(nested_key)
        if isinstance(nested, dict) and nested.get("equipment_id"):
            return nested["equipment_id"]
    return None


@router.get("/summary", status_code=status.HTTP_200_OK)
async def get_dashboard_summary(user: Annotated[dict, Depends(get_current_user)]):
    """
    Return aggregated dashboard data for the Flutter UI.

    Every figure is scoped to the caller's accessible equipment — see
    ``_accessible_equipment_ids``. A supervisor/executive sees everything
    (unchanged from before); a station-scoped engineer/technician now
    sees only their stations' equipment, plus anything with no recorded
    station, matching api.monitoring's existing visibility rule instead
    of a dashboard-only global view.

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
        allowed = _accessible_equipment_ids(db, user)

        work_order_query = db.query(WorkOrderRecord)
        if allowed is not None:
            work_order_query = work_order_query.filter(WorkOrderRecord.equipment_id.in_(allowed))
        work_order_count = work_order_query.count()

        # AuditLog has no equipment_id column (payload shapes vary — see
        # _audit_log_equipment_id), so these are scoped in Python after
        # loading rather than filtered in SQL like the queries above.
        alert_rows = db.query(AuditLog).filter(AuditLog.event_name == "ALERT_RECEIVED").all()
        alert_rows = [
            r for r in alert_rows
            if allowed is None or _audit_log_equipment_id(_load_payload(r)) in allowed | {None}
        ]
        alert_count = len(alert_rows)

        now = datetime.now(timezone.utc)
        recent_window = now - timedelta(hours=24)
        recent_alert_rows = [r for r in alert_rows if _normalize_timestamp(r.timestamp) >= recent_window]

        incident_equipment_ids = set()
        for record in recent_alert_rows:
            try:
                payload = json.loads(record.payload)
                incident_equipment_ids.add(payload.get("equipment_id"))
            except json.JSONDecodeError:
                continue

        incident_count = len(incident_equipment_ids)

        recent_work_order_query = db.query(WorkOrderRecord).filter(WorkOrderRecord.created_at >= recent_window)
        if allowed is not None:
            recent_work_order_query = recent_work_order_query.filter(WorkOrderRecord.equipment_id.in_(allowed))
        recent_work_orders = recent_work_order_query.all()
        current_statuses = {
            record.id: current_work_order_status(db, record.id)
            for record in recent_work_orders
        }
        open_work_orders = sum(
            status != "COMPLETED" for status in current_statuses.values()
        )

        external_source_rows = db.query(AuditLog).filter(AuditLog.event_name == "EXTERNAL_SOURCE_REQUIRED").all()
        external_source_alerts = sum(
            1 for r in external_source_rows
            if allowed is None or _audit_log_equipment_id(_load_payload(r)) in allowed | {None}
        )

        health_checks = []
        health_check_rows = (
            db.query(AuditLog)
            .filter(AuditLog.event_name == "TELEMETRY_CHECK")
            .order_by(AuditLog.timestamp.desc())
            .limit(5 if allowed is None else 200)  # scoped case needs more candidates before Python-side filtering+limit
            .all()
        )
        for record in health_check_rows:
            try:
                payload = json.loads(record.payload)
            except json.JSONDecodeError:
                continue

            telemetry = payload.get("telemetry", {})
            equipment_id = telemetry.get("equipment_id")
            if allowed is not None and equipment_id is not None and equipment_id not in allowed:
                continue
            health_checks.append(
                {
                    "equipment_id": equipment_id,
                    "temperature": telemetry.get("temperature"),
                    "vibration": telemetry.get("vibration"),
                    "installation_age_hours": telemetry.get("installation_age_hours"),
                    "risk_probability": payload.get("risk_probability"),
                    "health_status": payload.get("health_status"),
                    "checked_at": record.timestamp.isoformat(),
                }
            )
            if len(health_checks) == 5:
                break

        # Real downtime, from the same DowntimeWindow rows opened/closed by
        # work-order lifecycle transitions (see database/lifecycle.py) —
        # not a status/age heuristic. Matches the window /executive-summary
        # already uses, scoped to the same recent_window as the rest of
        # this endpoint's "recent" figures.
        recent_downtime_query = db.query(DowntimeWindow).filter(DowntimeWindow.started_at >= recent_window)
        if allowed is not None:
            recent_downtime_query = recent_downtime_query.filter(DowntimeWindow.equipment_id.in_(allowed))
        recent_downtime_windows = recent_downtime_query.all()
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
async def get_audit_logs(user: Annotated[dict, Depends(get_current_user)]):
    """Return recent audit log entries for the UI insights screen, scoped
    to the caller's accessible equipment — same rule as /summary above.
    Rows with no identifiable equipment_id (see _audit_log_equipment_id)
    stay visible to everyone, same as an equipment reading with no
    station_id."""
    db = SessionLocal()
    try:
        allowed = _accessible_equipment_ids(db, user)
        query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
        # Scoped callers need more candidates scanned before Python-side
        # filtering narrows it down to 50 — unscoped (supervisor/executive)
        # keeps the cheap SQL-side limit.
        records = query.limit(50 if allowed is None else 1000).all()
        if allowed is not None:
            records = [
                r for r in records
                if _audit_log_equipment_id(_load_payload(r)) in allowed | {None}
            ][:50]
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
