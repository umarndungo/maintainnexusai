"""Supabase Storage — signed upload URLs for close-out photo evidence.

Only ever called from ``api.notifications`` (photo-upload-url endpoint),
mirroring the single-call-site convention for external providers in
this codebase. A signed *upload* URL (not a proxy through this backend)
is issued so a large photo on a poor connection uploads directly to
Supabase — the backend host's own request-size limits never come into
the picture (Build Plan, Phase 4 step 5).
"""

import logging
import uuid
from typing import Any

import requests

from config import SUPABASE_PHOTOS_BUCKET, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL

logger = logging.getLogger(__name__)


def configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def create_signed_upload_url(work_order_id: str, extension: str = "jpg") -> dict[str, Any]:
    """Ask Supabase Storage for a one-time signed upload URL.

    Returns ``{"status": "OK", "upload_url": ..., "object_path": ...,
    "token": ...}`` on success, or ``{"status": "FAILED", "error": ...}``
    (including ``NOT_CONFIGURED`` when Supabase credentials are absent —
    the caller turns that into an HTTP 503, not a silent failure).
    """
    if not configured():
        return {"status": "NOT_CONFIGURED", "error": "Supabase Storage is not configured yet"}

    object_path = f"{work_order_id}/{uuid.uuid4().hex}.{extension}"
    url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/upload/sign/{SUPABASE_PHOTOS_BUCKET}/{object_path}"
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
            },
            timeout=10,
        )
        if response.status_code not in (200, 201):
            logger.error("Supabase signed-upload-url request failed: %s %s", response.status_code, response.text)
            return {"status": "FAILED", "error": f"Supabase returned {response.status_code}"}
        payload = response.json()
        signed_path = payload.get("url") or payload.get("signedURL") or ""
        return {
            "status": "OK",
            "upload_url": f"{SUPABASE_URL.rstrip('/')}/storage/v1{signed_path}" if signed_path.startswith("/") else signed_path,
            "object_path": object_path,
            "token": payload.get("token"),
        }
    except Exception as exc:
        logger.exception("Supabase signed-upload-url request errored")
        return {"status": "FAILED", "error": str(exc)}
