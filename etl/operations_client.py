"""Internal client for the decision engine's Act step — mirrors
etl/ml_client.py's/etl/readings_client.py's shape (an HTTP client, never
a direct DB write, matching every etl/*.py module's convention)."""

import requests

from config import API_INTERNAL_BASE_URL, INTERNAL_SERVICE_TOKEN

BASE_URL = API_INTERNAL_BASE_URL
_HEADERS = {"X-Internal-Service": INTERNAL_SERVICE_TOKEN}


def request_reassignment(
    equipment_id: str,
    asset_type: str,
    risk_level: str,
    reading_id: int | None = None,
) -> dict | None:
    """Ask the decision engine's Act step to evaluate (and, if warranted,
    apply) a loading-point reassignment for this reading. Returns the
    endpoint's JSON body, or None on a network/timeout failure — a
    failure here never blocks the existing alert/work-order path, which
    is why this is a best-effort call, not a raised exception."""
    try:
        response = requests.post(
            f"{BASE_URL}/operations/loading-points/reassign",
            json={
                "equipment_id": equipment_id,
                "asset_type": asset_type,
                "risk_level": risk_level,
                "reading_id": reading_id,
            },
            headers=_HEADERS,
            timeout=10,
        )
    except requests.RequestException:
        return None
    if response.status_code not in (200, 201):
        return None
    return response.json()
