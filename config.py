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