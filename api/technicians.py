"""
HR Technicians Module — Shift & Certification Lookup.

Provides a filtered view of the technician workforce, allowing the ETL
pipeline to find an available, certified technician for a given work
order. Uses an in-memory roster as a stand-in for a full HR system.
"""

import random
from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter(prefix="/api/v1/hr/technicians", tags=["HR"])

_TECHNICIAN_NAMES = [
    "Alice W.",
    "Bob M.",
    "Clara J.",
    "Daniel K.",
    "Eva L.",
]

_CERT_SETS = [
    ["PUMP_SEAL", "HIGH_VOLTAGE"],
    ["PUMP_SEAL"],
    ["ELECTRICAL"],
    ["MECHANICAL", "PUMP_SEAL"],
    ["CONTROL_SYSTEMS"],
]


def _generate_technicians():
    technicians = []
    for index, name in enumerate(_TECHNICIAN_NAMES, start=101):
        technicians.append(
            {
                "id": f"TECH-{index}",
                "name": name,
                "on_shift": index % 2 == 1,
                "certs": random.choice(_CERT_SETS),
            }
        )
    return technicians


TECHNICIANS = _generate_technicians()


@router.get("/available", responses={404: {"description": "No eligible technician available on shift"}})
async def get_available_technicians(required_cert: Optional[str] = None):
    """
    Return technicians who are currently on shift, optionally filtered by
    a required certification.

    Query Parameters
    ----------------
    required_cert : str, optional
        If provided, only technicians holding this certification are returned.

    Returns
    -------
    dict
        - available_technicians : list of matching technician records

    Raises
    ------
    HTTPException (404)
        If no on-shift technician satisfies the filter criteria.
    """
    # Filter: must be on shift AND (no cert filter OR cert is possessed)
    match = [
        t
        for t in TECHNICIANS
        if t["on_shift"]
        and (not required_cert or required_cert in t["certs"])
    ]
    if not match:
        raise HTTPException(
            status_code=404, detail="No eligible technician available on shift"
        )
    return {"available_technicians": match}
