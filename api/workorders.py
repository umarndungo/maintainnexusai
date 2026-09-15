"""
Work Orders Module — Technician Dispatch Endpoint & DB Persistence.

Creates a work order that assigns a certified technician to repair a
specific piece of equipment using a designated replacement part. The
order is persisted to both the in-memory response and the PostgreSQL
``work_orders`` table.
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from database.db import SessionLocal
from database.lifecycle import append_lifecycle_event, current_work_order_status
from database.models import WorkOrderRecord
from api.auth import require_internal_or_user, require_roles
from database.models import DowntimeWindow, WorkOrderLifecycleEvent
from api.events import publish_event

router = APIRouter(
    prefix="/api/v1/maintenance",
    tags=["Work Orders"],
    dependencies=[Depends(require_internal_or_user)],
)


def _normalize_timestamp(created_at: datetime) -> datetime:
    if created_at is None:
        return created_at
    if created_at.tzinfo is None:
        return created_at.replace(tzinfo=timezone.utc)
    return created_at.astimezone(timezone.utc)


def _elapsed_seconds(created_at: datetime) -> int:
    created_at = _normalize_timestamp(created_at)
    return int((datetime.now(timezone.utc) - created_at).total_seconds())


class WorkOrderCreate(BaseModel):
    """
    Payload required to dispatch a new work order.

    Attributes
    ----------
    equipment_id  : str — asset needing repair
    technician_id : str — id of the assigned technician
    part_number   : str — replacement part to use
    alert_task_id : str | None — optional upstream alert identifier
    """
    equipment_id: str
    technician_id: str
    part_number: str
    alert_task_id: str | None = None


@router.post("/work-orders", status_code=status.HTTP_201_CREATED)
async def create_work_order(wo: WorkOrderCreate):
    """
    Dispatch a new work order and persist to PostgreSQL.

    The work order lifecycle is:
        CREATED → PARTS_RESERVED → DISPATCHED

    On creation the status is set to ``DISPATCHED`` to reflect that
    all pre-checks (stock, technician) have already been performed
    by the pipeline.

    Returns
    -------
    dict
        - work_order_id  : unique identifier (e.g. "WO-A1B2C3D4")
        - equipment_id   : the asset being repaired
        - technician_id  : the assigned technician
        - part_number    : the replacement part
        - status         : "DISPATCHED"
        - lifecycle      : full state history
        - alert_task_id  : optional upstream alert identifier for correlation with the originating alert
    """
    wo_id = f"WO-{uuid.uuid4().hex[:8].upper()}"
    created_at = datetime.now(timezone.utc)

    # Persist to PostgreSQL
    db = SessionLocal()
    try:
        # Guard against a duplicate alert_task_id at the endpoint itself —
        # not just upstream in tasks._find_existing_work_order_by_task_id,
        # which only protects the one automated caller (the Celery
        # pipeline). Any other caller hitting this endpoint twice for the
        # same alert would otherwise create two work orders for it.
        # etl/load.dispatch_work_order already expects and handles this
        # exact 409 (02-BACKEND-GUIDE.md §3).
        if wo.alert_task_id is not None:
            existing = (
                db.query(WorkOrderRecord)
                .filter(WorkOrderRecord.alert_task_id == wo.alert_task_id)
                .first()
            )
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A work order already exists for alert_task_id {wo.alert_task_id!r}: {existing.id}",
                )

        record = WorkOrderRecord(
            id=wo_id,
            equipment_id=wo.equipment_id,
            technician_id=wo.technician_id,
            part_number=wo.part_number,
            alert_task_id=wo.alert_task_id,
            created_at=created_at,
        )
        db.add(record)
        db.flush()
        append_lifecycle_event(
            db,
            work_order_id=wo_id,
            to_status="PENDING_APPROVAL",
            actor_id="system",
            actor_role="internal",
            note="Work order created from validated alert",
        )
        # So connected dashboards see the ETL pipeline dispatch a new work
        # order live, not only later manual approve/reject/escalate actions
        # (which already published via _transition).
        _publish_lifecycle_event(record, "PENDING_APPROVAL")
        db.commit()
    finally:
        db.close()

    response = {
        "work_order_id": wo_id,
        "equipment_id": wo.equipment_id,
        "assigned_technician_id": wo.technician_id,
        "reserved_part": wo.part_number,
                "status": "PENDING_APPROVAL",
        "created_at": created_at.isoformat(),
        "duration_seconds": 0,
        "lifecycle_history": [
            "ALERT_RECEIVED",
            "DISPATCHED",
            "PROCESSING",
            "EXECUTED",
        ],
    }

    if wo.alert_task_id is not None:
        response["alert_task_id"] = wo.alert_task_id

    return response


def _publish_lifecycle_event(record: WorkOrderRecord, to_status: str) -> None:
    publish_event({
        "type": "work_order.lifecycle",
        "work_order_id": record.id,
        "equipment_id": record.equipment_id,
        "technician_id": record.technician_id,
        "to_status": to_status,
    })


def _get_work_order(db, work_order_id: str) -> WorkOrderRecord:
    record = db.query(WorkOrderRecord).filter(WorkOrderRecord.id == work_order_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Work order not found")
    return record


def _transition(db, record, to_status: str, actor: dict, note: str):
    current = current_work_order_status(db, record.id)
    allowed = {
        "PENDING_APPROVAL": {"APPROVED", "REJECTED", "ESCALATED"},
        "ESCALATED": {"APPROVED", "REJECTED"},
        "APPROVED": {"DISPATCHED"},
        "DISPATCHED": {"IN_PROGRESS"},
        "IN_PROGRESS": {"COMPLETED"},
    }
    if to_status not in allowed.get(current, set()):
        raise HTTPException(status_code=409, detail=f"Cannot transition from {current} to {to_status}")
    event = append_lifecycle_event(
        db,
        work_order_id=record.id,
        from_status=current,
        to_status=to_status,
        actor_id=actor["id"],
        actor_role=actor["role"],
        note=note,
    )
    if to_status == "DISPATCHED":
        open_window = db.query(DowntimeWindow).filter(
            DowntimeWindow.equipment_id == record.equipment_id,
            DowntimeWindow.ended_at.is_(None),
        ).first()
        if open_window is None:
            db.add(DowntimeWindow(
                equipment_id=record.equipment_id,
                work_order_id=record.id,
                started_at=event.timestamp,
                cause_alert_id=record.alert_task_id,
            ))
        # Fire the dispatch notification (SMS + push) — Build Plan Phase 2
        # step 3. Safe to enqueue before this transaction commits: the
        # task only reads WorkOrderRecord's base columns (equipment_id,
        # technician_id, part_number), which were already committed when
        # the record was first created. Deferred import: tasks.py imports
        # from api.* at module load, so importing it back here at module
        # load would cycle.
        from tasks import notify_dispatch

        notify_dispatch.delay(record.id)
    elif to_status == "COMPLETED":
        window = db.query(DowntimeWindow).filter(
            DowntimeWindow.work_order_id == record.id,
            DowntimeWindow.ended_at.is_(None),
        ).first()
        if window is not None:
            window.ended_at = event.timestamp
    _publish_lifecycle_event(record, to_status)
    db.flush()
    return event


def advance_work_order_status(work_order_id: str, actor: dict, to_status: str, note: str):
    """Apply one lifecycle transition and return the usual status dict.

    This is the single lifecycle-event writer every status change goes
    through — the three HTTP actions below, the dispatch-notification
    task, *and* the inbound-SMS-reply handler (api/notifications.py)
    all call this, so a technician replying "1" from a feature phone
    produces exactly the same kind of audit-chained event as tapping
    the button in the app (Build Plan Phase 3 step 4: "no separate code
    path, so the audit trail doesn't fork").
    """
    db = SessionLocal()
    try:
        record = _get_work_order(db, work_order_id)
        if actor["role"] not in {"engineer", "supervisor", "technician", "internal"}:
            raise HTTPException(status_code=403, detail="Insufficient role")
        event = _transition(db, record, to_status, actor, note)
        if to_status == "APPROVED":
            _transition(db, record, "DISPATCHED", actor, "Dispatch after approval")
        db.commit()
        return {"work_order_id": record.id, "status": current_work_order_status(db, record.id), "event_id": event.id}
    finally:
        db.close()


@router.patch("/work-orders/{work_order_id}/approve")
async def approve_work_order(work_order_id: str, actor: Annotated[dict, Depends(require_roles("engineer", "supervisor"))]):
    return advance_work_order_status(work_order_id, actor, "APPROVED", "Approved by authorized reviewer")


@router.patch("/work-orders/{work_order_id}/reject")
async def reject_work_order(work_order_id: str, actor: Annotated[dict, Depends(require_roles("engineer", "supervisor"))]):
    return advance_work_order_status(work_order_id, actor, "REJECTED", "Rejected by authorized reviewer")


@router.patch("/work-orders/{work_order_id}/escalate")
async def escalate_work_order(work_order_id: str, actor: Annotated[dict, Depends(require_roles("supervisor", "internal"))]):
    return advance_work_order_status(work_order_id, actor, "ESCALATED", "Approval exceeded SLA")


class WorkOrderComplete(BaseModel):
    """Close-out payload — Mobile spec Mockup 5 (notes, parts used, photo)."""

    notes: str | None = None
    parts_used: list[str] | None = None
    photo_object_path: str | None = None


@router.patch("/work-orders/{work_order_id}/complete")
async def complete_work_order(
    work_order_id: str,
    body: WorkOrderComplete,
    actor: Annotated[dict, Depends(require_roles("technician", "engineer", "supervisor"))],
):
    """Close out a work order: notes/parts/photo captured together as the
    audit record, per the spec's close-out screen. ``photo_object_path``
    comes from a prior call to the signed-upload-url endpoint
    (api/notifications.py) followed by the client's direct upload to
    Supabase Storage — this call only records where it landed."""
    result = advance_work_order_status(work_order_id, actor, "COMPLETED", "Closed out with notes/parts/photo")
    db = SessionLocal()
    try:
        record = _get_work_order(db, work_order_id)
        if body.notes is not None:
            record.completion_notes = body.notes
        if body.parts_used is not None:
            record.parts_used = ", ".join(body.parts_used)
        if body.photo_object_path is not None:
            record.photo_object_path = body.photo_object_path
        db.commit()
    finally:
        db.close()
    return result


@router.get("/work-orders/{work_order_id}/lifecycle")
async def work_order_lifecycle(work_order_id: str):
    db = SessionLocal()
    try:
        _get_work_order(db, work_order_id)
        events = db.query(WorkOrderLifecycleEvent).filter(
            WorkOrderLifecycleEvent.work_order_id == work_order_id
        ).order_by(WorkOrderLifecycleEvent.id.asc()).all()
        return [{
            "id": event.id,
            "from_status": event.from_status,
            "to_status": event.to_status,
            "actor_id": event.actor_id,
            "actor_role": event.actor_role,
            "timestamp": event.timestamp.isoformat(),
            "note": event.note,
            "event_hash": event.event_hash,
            "previous_event_hash": event.previous_event_hash,
        } for event in events]
    finally:
        db.close()


@router.get("/work-orders", status_code=status.HTTP_200_OK)
async def list_work_orders():
    """
    Return all dispatched work orders persisted in PostgreSQL.

    Returns
    -------
    list[dict]
        A list of work order records.
    """
    db = SessionLocal()
    try:
        records = (
            db.query(WorkOrderRecord)
            .order_by(WorkOrderRecord.created_at.desc())
            .all()
        )
        work_orders = [
            {
                "work_order_id": record.id,
                "equipment_id": record.equipment_id,
                "assigned_technician_id": record.technician_id,
                "reserved_part": record.part_number,
                "status": current_work_order_status(db, record.id),
                "created_at": record.created_at.isoformat(),
                "duration_seconds": _elapsed_seconds(record.created_at),
                "alert_task_id": record.alert_task_id,
            }
            for record in records
        ]
        return work_orders
    finally:
        db.close()
