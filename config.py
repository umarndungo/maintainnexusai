"""Centralized runtime configuration sourced from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


API_BASE_URL = _env("API_BASE_URL", "http://localhost:8000/api/v1")
API_INTERNAL_BASE_URL = _env("API_INTERNAL_BASE_URL", API_BASE_URL)
DATABASE_URL = _env(
    "DATABASE_URL",
    "postgresql://admin:secret@localhost:5432/maintain_db",
)
CELERY_BROKER_URL = _env("CELERY_BROKER_URL", "redis://localhost:6379/0")
AUTH_SECRET = _env("AUTH_SECRET", "change-me-in-production")
INTERNAL_SERVICE_TOKEN = _env("INTERNAL_SERVICE_TOKEN", "internal-dev-token")
API_HOST = _env("API_HOST", "0.0.0.0")
API_PORT = int(_env("API_PORT", "8000"))

# --- Africa's Talking (SMS) -------------------------------------------------
# Empty by default: the notification code treats a missing API key as
# "no provider configured yet" and logs + records SMS_LOG rows with
# status SKIPPED_NO_CREDENTIALS instead of failing, so the rest of the
# dispatch flow (push, lifecycle events) still runs tonight without an
# Africa's Talking account. Never commit real values here — set them on
# the host as secrets, same as every other credential in this file.
AFRICASTALKING_USERNAME = _env("AFRICASTALKING_USERNAME", "")
AFRICASTALKING_API_KEY = _env("AFRICASTALKING_API_KEY", "")
AFRICASTALKING_SENDER_ID = _env("AFRICASTALKING_SENDER_ID", "")
# Shared secret appended as ?token=... to the inbound-SMS webhook URL you
# give Africa's Talking, so a stranger can't POST fake replies that move
# work orders through their lifecycle. Empty means "not checked yet" —
# fine for tonight's testing, not for the real webhook URL.
AFRICASTALKING_INBOUND_TOKEN = _env("AFRICASTALKING_INBOUND_TOKEN", "")

# --- Firebase Cloud Messaging (push) ----------------------------------------
# Path to a Firebase service-account JSON key file. Empty by default —
# push send becomes a no-op (logged, not an error) until this is set.
FIREBASE_SERVICE_ACCOUNT_FILE = _env("FIREBASE_SERVICE_ACCOUNT_FILE", "")

# --- Supabase Storage (photo evidence) --------------------------------------
# Empty by default — the signed-upload-url endpoint returns 503 until
# these are set, rather than the client silently failing to upload.
SUPABASE_URL = _env("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = _env("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_PHOTOS_BUCKET = _env("SUPABASE_PHOTOS_BUCKET", "work-order-photos")