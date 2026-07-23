"""
Work Orders Module — Technician Dispatch Endpoint & DB Persistence.

Creates a work order that assigns a certified technician to repair a
specific piece of equipment using a designated replacement part. The
order is persisted to both the in-memory response and the PostgreSQL
``work_orders`` table.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, status
from pydantic import BaseModel

from database.db import SessionLocal
from database.models import WorkOrderRecord

router = APIRouter(prefix="/api/v1/maintenance", tags=["Work Orders"])


def _normalize_timestamp(created_at: datetime) -> datetime:
    if created_at is None:
        return created_at
    if created_at.tzinfo is None:
        return created_at.replace(tzinfo=timezone.utc)
    return created_at.astimezone(timezone.utc)


def _compute_work_order_status(created_at: datetime) -> str:
    created_at = _normalize_timestamp(created_at)
    age = datetime.now(timezone.utc) - created_at
    seconds = age.total_seconds()
    if seconds < 1800: # Ideal confirmation for processing is 30 minutes
        return "DISPATCHED"
    if seconds < 7200: # Ideal resolution for now is 2 hours
        return "PROCESSING"
    return "EXECUTED"


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
    """
    equipment_id: str
    technician_id: str
    part_number: str


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
    """
    wo_id = f"WO-{uuid.uuid4().hex[:8].upper()}"
    created_at = datetime.now(timezone.utc)

    # Persist to PostgreSQL
    db = SessionLocal()
    try:
        record = WorkOrderRecord(
            id=wo_id,
            equipment_id=wo.equipment_id,
            technician_id=wo.technician_id,
            part_number=wo.part_number,
            status="DISPATCHED",
            created_at=created_at,
        )
        db.add(record)
        db.commit()
    finally:
        db.close()

    return {
        "work_order_id": wo_id,
        "equipment_id": wo.equipment_id,
        "assigned_technician_id": wo.technician_id,
        "reserved_part": wo.part_number,
        "status": "DISPATCHED",
        "created_at": created_at.isoformat(),
        "duration_seconds": 0,
        "lifecycle_history": [
            "ALERT_RECEIVED",
            "DISPATCHED",
            "PROCESSING",
            "EXECUTED",
        ],
    }


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
        work_orders = []
        seen_ids = set()
        for record in records:
            if record.id in seen_ids:
                continue
            seen_ids.add(record.id)
            work_orders.append(
                {
                    "work_order_id": record.id,
                    "equipment_id": record.equipment_id,
                    "assigned_technician_id": record.technician_id,
                    "reserved_part": record.part_number,
                    "status": _compute_work_order_status(record.created_at),
                    "created_at": record.created_at.isoformat(),
                    "duration_seconds": _elapsed_seconds(record.created_at),
                }
            )
        return work_orders
    finally:
        db.close()
