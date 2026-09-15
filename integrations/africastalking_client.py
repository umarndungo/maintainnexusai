"""Africa's Talking SMS provider — the *only* place the provider SDK is
called from (per 06-INTEGRATIONS-GUIDE.md §2: "wrap it behind that one
internal endpoint — don't call the provider SDK from multiple places").
``api.notifications`` is that one call site.

No credentials configured is treated as a normal, expected state
tonight (see config.py) — every call still returns a well-formed result
so the caller can log it to ``sms_log`` uniformly, it just never hits
the network.
"""

import logging
from typing import Any

from config import AFRICASTALKING_API_KEY, AFRICASTALKING_SENDER_ID, AFRICASTALKING_USERNAME

logger = logging.getLogger(__name__)

_sms_service = None
_init_failed = False


def _get_sms_service():
    """Lazily construct the Africa's Talking SMS service.

    Lazy + memoized: importing the ``africastalking`` SDK when no
    credentials exist yet isn't useful, and repeatedly re-initializing
    it per-request would be wasteful once they do.
    """
    global _sms_service, _init_failed
    if _sms_service is not None or _init_failed:
        return _sms_service
    try:
        import africastalking

        africastalking.initialize(AFRICASTALKING_USERNAME, AFRICASTALKING_API_KEY)
        _sms_service = africastalking.SMS
    except Exception:
        logger.exception("Africa's Talking SDK initialization failed")
        _init_failed = True
    return _sms_service


def send_sms(recipient: str, message: str) -> dict[str, Any]:
    """Send one SMS. Always returns a dict with at least a ``status`` key:

    - ``SKIPPED_NO_CREDENTIALS`` — no API key configured (expected until
      Phase 0/1 account setup is done).
    - ``SENT`` — accepted by Africa's Talking, with ``provider_message_id``.
    - ``FAILED`` — the SDK call raised or the provider rejected it, with
      an ``error`` string.
    """
    if not AFRICASTALKING_API_KEY or not AFRICASTALKING_USERNAME:
        logger.info("SMS to %s skipped: no Africa's Talking credentials configured.", recipient)
        return {"status": "SKIPPED_NO_CREDENTIALS"}

    service = _get_sms_service()
    if service is None:
        return {"status": "FAILED", "error": "Africa's Talking SDK failed to initialize"}

    try:
        kwargs: dict[str, Any] = {}
        if AFRICASTALKING_SENDER_ID:
            kwargs["sender_id"] = AFRICASTALKING_SENDER_ID
        response = service.send(message, [recipient], **kwargs)
        recipients = response.get("SMSMessageData", {}).get("Recipients", [])
        first = recipients[0] if recipients else {}
        status = str(first.get("status", "")).lower()
        if status == "success":
            return {"status": "SENT", "provider_message_id": first.get("messageId")}
        return {"status": "FAILED", "error": first.get("status") or "Unknown provider error"}
    except Exception as exc:
        logger.exception("Africa's Talking send failed for %s", recipient)
        return {"status": "FAILED", "error": str(exc)}
