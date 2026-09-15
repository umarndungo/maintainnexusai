"""Internal client for the equipment-readings ETL Load step — mirrors
etl/ml_client.py's shape. This is what makes the telemetry ETL's Load
step a real, durable write that happens *before* ML scoring: Celery
calls this to persist the validated/transformed reading, gets a
reading_id back, calls ML, then calls back here to attach the score.

Kept as an HTTP client rather than a direct DB write to match every
other etl/*.py module — none of them open a Postgres connection
directly; they all talk to web_api over the internal service boundary.
"""

import requests

from config import API_INTERNAL_BASE_URL, INTERNAL_SERVICE_TOKEN

BASE_URL = API_INTERNAL_BASE_URL
_HEADERS = {"X-Internal-Service": INTERNAL_SERVICE_TOKEN}


def create_reading(equipment_id: str, asset_type: str, telemetry: dict, station_id: str | None = None) -> int | None:
    """Load step: persist the validated/transformed reading. Returns the
    new row's id, or None if the call failed (network error or non-200)."""
    try:
        response = requests.post(
            f"{BASE_URL}/monitoring/readings",
            json={
                "equipment_id": equipment_id,
                "asset_type": asset_type,
                "station_id": station_id,
                "telemetry": telemetry,
            },
            headers=_HEADERS,
            timeout=10,
        )
    except requests.RequestException:
        return None
    if response.status_code != 201:
        return None
    return response.json().get("reading_id")


def update_reading_score(
    reading_id: int,
    risk_probability: float,
    risk_level: str | None,
    model_version: str | None,
    top_features: list | None,
    alert_created: bool,
) -> bool:
    """Attach an ML score to an already-loaded reading. Best-effort: a
    failure here means the reading stays unscored, not lost — the row
    from create_reading() already exists."""
    try:
        response = requests.patch(
            f"{BASE_URL}/monitoring/readings/{reading_id}",
            json={
                "risk_probability": risk_probability,
                "risk_level": risk_level,
                "model_version": model_version,
                "top_features": top_features or [],
                "alert_created": alert_created,
            },
            headers=_HEADERS,
            timeout=10,
        )
    except requests.RequestException:
        return False
    return response.status_code == 200
