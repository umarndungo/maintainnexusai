"""Firebase Cloud Messaging — the only place the Firebase Admin SDK is
called from, mirroring the "one call site" rule for the SMS provider
(06-INTEGRATIONS-GUIDE.md §2). Called from ``api.notifications`` only.

No service-account file configured is a normal state tonight — every
call still returns a well-formed result instead of raising, so the
dispatch flow degrades to "SMS only" rather than failing outright.
"""

import logging
from typing import Any

from config import FIREBASE_SERVICE_ACCOUNT_FILE

logger = logging.getLogger(__name__)

_app = None
_init_failed = False


def _get_app():
    global _app, _init_failed
    if _app is not None or _init_failed:
        return _app
    if not FIREBASE_SERVICE_ACCOUNT_FILE:
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_FILE)
        _app = firebase_admin.initialize_app(cred)
    except Exception:
        logger.exception("Firebase Admin SDK initialization failed")
        _init_failed = True
    return _app


def send_push(device_token: str, title: str, body: str, data: dict[str, str] | None = None) -> dict[str, Any]:
    """Send one push notification. Always returns a dict with a ``status``:
    ``SKIPPED_NO_CREDENTIALS``, ``SENT`` (with ``provider_message_id``), or
    ``FAILED`` (with ``error``)."""
    if not FIREBASE_SERVICE_ACCOUNT_FILE:
        logger.info("Push to device %s skipped: no Firebase service account configured.", device_token)
        return {"status": "SKIPPED_NO_CREDENTIALS"}

    app = _get_app()
    if app is None:
        return {"status": "FAILED", "error": "Firebase Admin SDK failed to initialize"}

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            token=device_token,
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
        )
        message_id = messaging.send(message)
        return {"status": "SENT", "provider_message_id": message_id}
    except Exception as exc:
        logger.exception("FCM send failed for device %s", device_token)
        return {"status": "FAILED", "error": str(exc)}
