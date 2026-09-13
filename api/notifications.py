"""Internal notification gateway; provider integration is intentionally isolated."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth import require_internal_service

router = APIRouter(
    prefix="/api/v1/notifications",
    tags=["Notifications"],
    dependencies=[Depends(require_internal_service)],
)


class SMSRequest(BaseModel):
    recipient: str
    message: str
    work_order_id: str | None = None


@router.post("/sms", status_code=202)
async def send_sms(request: SMSRequest):
    """Accept an internal notification request without exposing a provider to users."""
    return {"status": "queued", "recipient": request.recipient, "work_order_id": request.work_order_id}