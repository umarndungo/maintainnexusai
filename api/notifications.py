"""
Notifications Module — SMS, Push, and the Non-Smartphone SMS-Reply Path.

Build Plan phases 2 & 3. Every provider SDK call (Africa's Talking,
Firebase Admin, Supabase Storage) happens in ``integrations/*`` and is
called from exactly one place in this file each — see
06-INTEGRATIONS-GUIDE.md §2.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from pydantic import BaseModel

from api.auth import get_current_user, require_internal_service
from config import AFRICASTALKING_INBOUND_TOKEN
from database.auditing import append_audit_log
from database.db import SessionLocal
from database.models import PendingSmsPrompt, SmsLog, TechnicianDevice
from integrations import africastalking_client, fcm_client, supabase_storage

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/notifications",
    tags=["Notifications"],
    dependencies=[Depends(require_internal_service)],
)

# Endpoints a signed-in technician calls directly (device registration,
# requesting an upload URL) don't go through every other maintenance
# gateway route, so they get their own un-prefixed-dependency router and
# are included separately in api/main.py.
public_router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


def _write_sms_log(work_order_id: str | None, recipient: str, message: str, result: dict) -> None:
    db = SessionLocal()
    try:
        db.add(SmsLog(
            work_order_id=work_order_id,
            recipient=recipient,
            message=message,
            status=result.get("status", "UNKNOWN"),
            provider_message_id=result.get("provider_message_id"),
            error=result.get("error"),
        ))
        db.commit()
    finally:
        db.close()


class SMSRequest(BaseModel):
    recipient: str
    message: str
    work_order_id: str | None = None


@router.post("/sms", status_code=status.HTTP_202_ACCEPTED)
async def send_sms(request: SMSRequest):
    """Send one SMS via Africa's Talking and log the attempt to `sms_log`
    regardless of outcome (06-INTEGRATIONS-GUIDE.md §2)."""
    result = africastalking_client.send_sms(request.recipient, request.message)
    _write_sms_log(request.work_order_id, request.recipient, request.message, result)
    return {"status": "queued", "recipient": request.recipient, "work_order_id": request.work_order_id, "provider_result": result}


class PushRequest(BaseModel):
    device_token: str
    title: str
    body: str
    data: dict[str, str] = {}
    work_order_id: str | None = None


@router.post("/push", status_code=status.HTTP_202_ACCEPTED)
async def send_push(request: PushRequest):
    """Send one FCM push. Not logged to `sms_log` (different channel) —
    delivery failures here are non-fatal since SMS already went out in
    parallel for the same dispatch."""
    result = fcm_client.send_push(request.device_token, request.title, request.body, request.data)
    return {"status": "queued", "work_order_id": request.work_order_id, "provider_result": result}


class DeviceRegistration(BaseModel):
    device_token: str
    platform: str | None = None


@public_router.post("/register-device", status_code=status.HTTP_200_OK)
async def register_device(body: DeviceRegistration, user: Annotated[dict, Depends(get_current_user)]):
    """Called by the mobile app right after sign-in so dispatch pushes
    have somewhere to go. One row per technician — a new sign-in on a
    different device just overwrites the old token."""
    db = SessionLocal()
    try:
        existing = db.query(TechnicianDevice).filter(TechnicianDevice.technician_id == user["id"]).first()
        if existing:
            existing.device_token = body.device_token
            existing.platform = body.platform
            existing.updated_at = datetime.now(timezone.utc)
        else:
            db.add(TechnicianDevice(technician_id=user["id"], device_token=body.device_token, platform=body.platform))
        db.commit()
    finally:
        db.close()
    return {"status": "registered"}


class PhotoUploadUrlRequest(BaseModel):
    work_order_id: str
    extension: str = "jpg"


@public_router.post("/photo-upload-url", status_code=status.HTTP_200_OK)
async def photo_upload_url(
    body: PhotoUploadUrlRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Issue a signed Supabase Storage upload URL for one close-out
    photo (Build Plan Phase 4 step 5). The client uploads directly to
    the returned URL; only the resulting object path is later recorded
    against the work order via PATCH .../complete."""
    result = supabase_storage.create_signed_upload_url(body.work_order_id, body.extension)
    if result["status"] == "NOT_CONFIGURED":
        raise HTTPException(status_code=503, detail="Photo storage is not configured yet")
    if result["status"] != "OK":
        raise HTTPException(status_code=502, detail=result.get("error", "Photo storage request failed"))
    return result


# ---------------------------------------------------------------------------
# Non-smartphone SMS-reply path (Build Plan Phase 3)
# ---------------------------------------------------------------------------

def create_pending_prompt(phone_number: str, work_order_id: str, code_to_status: dict[str, str], ttl_hours: int = 24) -> None:
    """Record an outstanding reply prompt. Called from tasks.notify_dispatch
    when the assigned technician is flagged non-smartphone."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        db.add(PendingSmsPrompt(
            phone_number=phone_number,
            work_order_id=work_order_id,
            expected_codes=",".join(code_to_status.keys()),
            code_to_status=json.dumps(code_to_status),
            sent_at=now,
            expires_at=now + timedelta(hours=ttl_hours),
        ))
        db.commit()
    finally:
        db.close()


@public_router.post("/sms/inbound", status_code=status.HTTP_200_OK)
async def inbound_sms(
    from_: Annotated[str, Form(alias="from")],
    text: Annotated[str, Form()] = "",
    token: str | None = Query(None),
):
    """Africa's Talking POSTs inbound replies as an
    ``application/x-www-form-urlencoded`` body with ``from``/``text``
    fields — the shared secret instead rides as a ``?token=`` query
    param on the webhook URL you register with them (config.py's
    AFRICASTALKING_INBOUND_TOKEN). Matches on phone number + the
    *exact* echoed code — never "most recent open prompt" for that
    number, since a technician can have more than one job queued
    (Build Plan Phase 3 step 3)."""
    if AFRICASTALKING_INBOUND_TOKEN and token != AFRICASTALKING_INBOUND_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid inbound token")

    reply_code = text.strip().split()[0] if text.strip() else ""
    now = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        candidates = (
            db.query(PendingSmsPrompt)
            .filter(
                PendingSmsPrompt.phone_number == from_,
                PendingSmsPrompt.resolved_at.is_(None),
                PendingSmsPrompt.expires_at >= now,
            )
            .all()
        )
        matches = [p for p in candidates if reply_code in p.expected_codes.split(",")]

        if not matches:
            _log_unmatched_reply(from_, text, reason="no_open_prompt_with_that_code")
            return {"status": "unmatched"}
        if len(matches) > 1:
            # Genuinely ambiguous (two open jobs both accept the same
            # digit) — log it and do nothing rather than guess which
            # work order the technician meant.
            _log_unmatched_reply(from_, text, reason="ambiguous_multiple_open_prompts")
            return {"status": "ambiguous"}

        prompt = matches[0]
        code_to_status = json.loads(prompt.code_to_status)
        to_status = code_to_status.get(reply_code)
        # Read everything needed after the session closes into plain
        # locals now — `prompt` becomes a detached instance the moment
        # db.close() runs, and accessing its attributes after that
        # (even ones already loaded) triggers SQLAlchemy to try to
        # refresh them against a session that no longer exists.
        prompt_work_order_id = prompt.work_order_id
        # Only resolve (stop matching) once the *terminal* code fires —
        # "Reply 1=Accept 3=Complete" is two replies against the same
        # prompt, potentially hours apart. Resolving after "1" would
        # make "3" un-matchable later. COMPLETED is the one status nothing
        # in api.workorders' transition map ever leaves, so it's a safe,
        # generic stand-in for "no further reply is expected" rather than
        # hardcoding the digit "3".
        if to_status == "COMPLETED":
            prompt.resolved_at = now
        db.commit()
    finally:
        db.close()

    if not to_status:
        _log_unmatched_reply(from_, text, reason="code_not_mapped")
        return {"status": "unmatched"}

    # Same lifecycle-event writer every other status update goes through
    # — no separate code path (Build Plan Phase 3 step 4).
    from api.workorders import advance_work_order_status

    result = advance_work_order_status(
        prompt_work_order_id,
        actor={"id": _technician_id_for_phone(from_) or from_, "role": "technician"},
        to_status=to_status,
        note=f"Advanced via SMS reply {reply_code!r} from {from_}",
    )
    # `result` already carries its own "status" (the work order's new
    # lifecycle status) — nest it rather than spreading, or it would
    # silently clobber "applied" below with e.g. "IN_PROGRESS".
    return {"status": "applied", "work_order": result}


def _technician_id_for_phone(phone_number: str) -> str | None:
    from api.technicians import TECHNICIANS

    for tech in TECHNICIANS:
        if tech.get("phone_number") == phone_number:
            return tech["id"]
    return None


def _log_unmatched_reply(phone_number: str, text: str, reason: str) -> None:
    db = SessionLocal()
    try:
        append_audit_log(db, "SMS_REPLY_UNMATCHED", {"phone_number": phone_number, "text": text, "reason": reason})
        db.commit()
    except Exception:
        logger.exception("Failed to write SMS_REPLY_UNMATCHED audit row")
        db.rollback()
    finally:
        db.close()


def expire_stale_prompts() -> int:
    """Expire prompts past their TTL. Called from tasks.expire_stale_sms_prompts
    on the same Celery Beat cadence as escalate_stale_approvals. Plain
    sync function (no I/O here is actually async) — called directly
    from the Celery task, not through asyncio."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        stale = (
            db.query(PendingSmsPrompt)
            .filter(PendingSmsPrompt.resolved_at.is_(None), PendingSmsPrompt.expires_at < now)
            .all()
        )
        for prompt in stale:
            prompt.resolved_at = now
        db.commit()
        return len(stale)
    finally:
        db.close()
