"""
Data Extraction Module — External API Fetchers.

Provides functions that call out to the MaintainNexus mock API services
(warehouse stock, HR technicians) and return the parsed JSON response.
Each function returns ``None`` if the upstream service is unavailable
or returns a non-success status code, giving the pipeline clean
failure-detection semantics.
"""

import os
import requests

# Base URL — configurable so the Celery worker can reach the web_api container.
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

# Map failure codes to required technician certifications.
# Extend this mapping as new equipment types are added.
FAILURE_CODE_TO_CERT = {
    "ERR_SEAL_LEAK": "PUMP_SEAL",
    "ERR_BEARING_WEAR": "ROTATING_EQUIPMENT",
    "ERR_OVERHEAT": "HVAC",
    "ERR_ELECTRICAL": "HIGH_VOLTAGE",
    "ERR_GENERAL": "GENERAL_MAINTENANCE",
}

DEFAULT_CERT = "GENERAL_MAINTENANCE"


def check_stock(part_number: str):
    """
    Look up the current inventory level for a replacement part.

    Calls ``GET /api/v1/warehouse/stock?part_number=...``.

    Parameters
    ----------
    part_number : str
        The part identifier to query.

    Returns
    -------
    dict or None
        Parsed JSON response on success, ``None`` on failure.
    """
    res = requests.get(
        f"{BASE_URL}/warehouse/stock", params={"part_number": part_number}
    )
    return res.json() if res.status_code == 200 else None


def get_technician(required_cert: str):
    """
    Fetch the first available on-shift technician who holds a given cert.

    Calls ``GET /api/v1/hr/technicians/available?required_cert=...``.

    Parameters
    ----------
    required_cert : str
        The certification credential required (e.g. ``"PUMP_SEAL"``).

    Returns
    -------
    dict or None
        The first matching technician record, or ``None`` if none found.
    """
    res = requests.get(
        f"{BASE_URL}/hr/technicians/available",
        params={"required_cert": required_cert},
    )
    if res.status_code == 200:
        data = res.json()
        if data.get("available_technicians"):
            return data["available_technicians"][0]  # take the first match
    return None


def resolve_cert_for_failure(failure_code: str) -> str:
    """
    Map a machine failure code to the required technician certification.

    Parameters
    ----------
    failure_code : str
        Machine-readable error code (e.g. ``"ERR_SEAL_LEAK"``).

    Returns
    -------
    str
        The certification string to pass to ``get_technician``.
    """
    return FAILURE_CODE_TO_CERT.get(failure_code, DEFAULT_CERT)
