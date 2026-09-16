"""
Operations Module — Predict -> Decide -> Act (loading-point reassignment).

docs/11-PRODUCT-CONTRACT.md's golden path: a critical pump/valve/arm's
risk crosses threshold -> the decision engine marks its loading bay
unavailable and reassigns the next scheduled truck to an alternate bay
-> the decision and action are recorded, durably and idempotently. The
existing alert -> work-order -> engineer-approval path (api/workorders.py)
is untouched and keeps running in parallel for the physical-repair side
of the same reading; this module only ever adds an operational-rerouting
record, it never blocks or replaces that path.

Deliberately simplified from the full contract for a first build — see
database/models.py's LoadingPoint/LoadingSlot docstrings for what's
elided (no standalone Truck entity; bays/slots are lazily self-seeded
here rather than pre-populated, since the equipment fleet is randomized
per-process (api/equipment.py) and a fixed seed can't reliably target
whichever pump actually shows up in a given run's generated telemetry).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.auth import require_internal_service, require_roles
from database.auditing import append_audit_log
from database.db import SessionLocal
from database.models import Decision, LoadingPoint, LoadingSlot, OperationalAction, OperationalOutcome

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/operations",
    tags=["Operations"],
    dependencies=[Depends(require_roles("engineer", "supervisor", "executive"))],
)

# The Act step itself is internal-only — called by the Celery pipeline,
# never a browser. "Requires_human_approval: false" is a property of this
# one action *type* (operational rerouting), not a statement that any
# authenticated user may trigger it; see the module docstring's safety note.
internal_router = APIRouter(
    prefix="/api/v1/operations",
    tags=["Operations"],
    dependencies=[Depends(require_internal_service)],
)


def _write_audit_log(event_name: str, payload: dict) -> None:
    db = SessionLocal()
    try:
        append_audit_log(db, event_name, payload)
        db.commit()
    finally:
        db.close()


def _get_or_create_bay(db, bay_code: str, equipment_id: str | None) -> LoadingPoint:
    bay = db.query(LoadingPoint).filter(LoadingPoint.bay_code == bay_code).first()
    if bay is None:
        bay = LoadingPoint(bay_code=bay_code, equipment_id=equipment_id)
        db.add(bay)
        db.flush()
    return bay


class ReassignmentRequest(BaseModel):
    equipment_id: str
    asset_type: str
    risk_level: str
    reading_id: int | None = None


@internal_router.post("/loading-points/reassign", status_code=status.HTTP_201_CREATED)
async def reassign_loading_point(body: ReassignmentRequest):
    """Decide + Act in one call: lazily ensure a bay/alternate/slot exist
    for this equipment (see module docstring), then reassign the
    scheduled truck to the alternate bay if it has capacity."""
    from etl.decision_engine import should_evaluate

    if not should_evaluate(body.risk_level):
        return {"status": "not_evaluated", "reason": f"risk_level {body.risk_level!r} below policy threshold"}

    db = SessionLocal()
    try:
        bay = _get_or_create_bay(db, f"BAY-{body.equipment_id}", body.equipment_id)

        # Check the *original* bay's own availability before touching
        # anything else — a repeat qualifying reading for equipment whose
        # bay was already pulled from service by an earlier decision must
        # not spawn a phantom new truck/slot there. Nothing to do until a
        # human/ops process brings the bay back online.
        if bay.capacity_status != "AVAILABLE":
            last_decision = (
                db.query(Decision)
                .filter(Decision.affected_equipment_id == body.equipment_id)
                .order_by(Decision.id.desc())
                .first()
            )
            result = {
                "status": "already_unavailable",
                "bay_code": bay.bay_code,
                "decision_id": last_decision.id if last_decision is not None else None,
            }
            db.commit()
            return result

        alternate = _get_or_create_bay(db, f"BAY-ALT-{body.equipment_id}", None)
        if alternate.capacity_status != "AVAILABLE":
            result = {"status": "no_capacity", "bay_code": bay.bay_code}
            db.commit()
            return result

        slot = (
            db.query(LoadingSlot)
            .filter(LoadingSlot.loading_point_id == bay.id, LoadingSlot.status == "SCHEDULED")
            .first()
        )
        if slot is None:
            slot = LoadingSlot(
                loading_point_id=bay.id,
                truck_code=f"TRUCK-{uuid.uuid4().hex[:6].upper()}",
                scheduled_arrival=datetime.now(timezone.utc),
                status="SCHEDULED",
            )
            db.add(slot)
            db.flush()

        # Stable across retries for the same equipment+truck — independent
        # of any fresh Decision row id — so retrying the exact same
        # not-yet-applied request (e.g. after a network timeout) resolves
        # to "already_applied" rather than reassigning the same truck twice.
        idempotency_key = f"{body.equipment_id}:{slot.truck_code}"
        existing_action = (
            db.query(OperationalAction)
            .filter(OperationalAction.idempotency_key == idempotency_key)
            .first()
        )
        if existing_action is not None:
            result = {
                "status": "already_applied",
                "action_id": existing_action.id,
                "decision_id": existing_action.decision_id,
            }
            db.commit()
            return result

        reason = (
            f"{body.equipment_id} risk_level={body.risk_level} exceeds policy threshold; "
            f"{bay.bay_code} marked unavailable, truck {slot.truck_code} reassigned to {alternate.bay_code}."
        )
        decision = Decision(
            reading_id=body.reading_id,
            decision_type="REASSIGN_LOADING_POINT",
            reason=reason,
            affected_equipment_id=body.equipment_id,
            requires_human_approval=False,
        )
        db.add(decision)
        db.flush()

        bay.capacity_status = "UNAVAILABLE"
        slot.loading_point_id = alternate.id
        slot.status = "REASSIGNED"

        action = OperationalAction(
            decision_id=decision.id,
            action_type="REASSIGN_LOADING_POINT",
            truck_code=slot.truck_code,
            original_loading_point_id=bay.id,
            new_loading_point_id=alternate.id,
            idempotency_key=idempotency_key,
            status="APPLIED",
        )
        db.add(action)
        db.flush()

        db.add(OperationalOutcome(action_id=action.id, action_success=True))

        # Captured into a plain dict *before* commit/close — an ORM
        # object's attributes aren't safely readable once its session
        # has closed (see api/notifications.py's inbound_sms for the bug
        # this exact pattern was written to avoid).
        result = {
            "status": "applied",
            "decision_id": decision.id,
            "action_id": action.id,
            "original_bay": bay.bay_code,
            "new_bay": alternate.bay_code,
            "truck_code": slot.truck_code,
            "reason": reason,
        }
        db.commit()
    finally:
        db.close()

    if result["status"] == "applied":
        _write_audit_log("OPERATIONAL_ACTION_APPLIED", result)
    return result


@router.get("/loading-points", status_code=status.HTTP_200_OK)
async def list_loading_points(user: Annotated[dict, Depends(require_roles("engineer", "supervisor", "executive"))]):
    db = SessionLocal()
    try:
        bays = db.query(LoadingPoint).order_by(LoadingPoint.id).all()
        result = [
            {
                "id": b.id,
                "bay_code": b.bay_code,
                "equipment_id": b.equipment_id,
                "station_id": b.station_id,
                "supported_product": b.supported_product,
                "capacity_status": b.capacity_status,
            }
            for b in bays
        ]
    finally:
        db.close()
    return {"loading_points": result}


@router.get("/loading-points/{loading_point_id}", status_code=status.HTTP_200_OK)
async def get_loading_point(
    loading_point_id: int,
    user: Annotated[dict, Depends(require_roles("engineer", "supervisor", "executive"))],
):
    db = SessionLocal()
    try:
        bay = db.query(LoadingPoint).filter(LoadingPoint.id == loading_point_id).first()
        if bay is None:
            raise HTTPException(status_code=404, detail="Loading point not found")
        slots = (
            db.query(LoadingSlot)
            .filter(LoadingSlot.loading_point_id == bay.id)
            .order_by(LoadingSlot.id.desc())
            .all()
        )
        result = {
            "id": bay.id,
            "bay_code": bay.bay_code,
            "equipment_id": bay.equipment_id,
            "station_id": bay.station_id,
            "supported_product": bay.supported_product,
            "capacity_status": bay.capacity_status,
            "slots": [
                {
                    "id": s.id,
                    "truck_code": s.truck_code,
                    "status": s.status,
                    "scheduled_arrival": s.scheduled_arrival.isoformat(),
                }
                for s in slots
            ],
        }
    finally:
        db.close()
    return result


@router.get("/decisions", status_code=status.HTTP_200_OK)
async def list_decisions(user: Annotated[dict, Depends(require_roles("engineer", "supervisor", "executive"))]):
    db = SessionLocal()
    try:
        decisions = db.query(Decision).order_by(Decision.id.desc()).limit(100).all()
        result = [
            {
                "id": d.id,
                "reading_id": d.reading_id,
                "decision_type": d.decision_type,
                "reason": d.reason,
                "affected_equipment_id": d.affected_equipment_id,
                "requires_human_approval": d.requires_human_approval,
                "created_at": d.created_at.isoformat(),
            }
            for d in decisions
        ]
    finally:
        db.close()
    return {"decisions": result}


@router.get("/decisions/{decision_id}", status_code=status.HTTP_200_OK)
async def get_decision(
    decision_id: int,
    user: Annotated[dict, Depends(require_roles("engineer", "supervisor", "executive"))],
):
    db = SessionLocal()
    try:
        decision = db.query(Decision).filter(Decision.id == decision_id).first()
        if decision is None:
            raise HTTPException(status_code=404, detail="Decision not found")
        action = db.query(OperationalAction).filter(OperationalAction.decision_id == decision.id).first()
        outcome = (
            db.query(OperationalOutcome).filter(OperationalOutcome.action_id == action.id).first()
            if action is not None
            else None
        )
        result = {
            "id": decision.id,
            "reading_id": decision.reading_id,
            "decision_type": decision.decision_type,
            "reason": decision.reason,
            "affected_equipment_id": decision.affected_equipment_id,
            "requires_human_approval": decision.requires_human_approval,
            "policy_version": decision.policy_version,
            "created_at": decision.created_at.isoformat(),
            "action": {
                "id": action.id,
                "action_type": action.action_type,
                "truck_code": action.truck_code,
                "status": action.status,
                "idempotency_key": action.idempotency_key,
            }
            if action is not None
            else None,
            "outcome": {
                "action_success": outcome.action_success,
                "actual_failure": outcome.actual_failure,
                "actual_delay_minutes": outcome.actual_delay_minutes,
                "alternate_bay_completed": outcome.alternate_bay_completed,
            }
            if outcome is not None
            else None,
        }
    finally:
        db.close()
    return result
