"""
HR Technicians Module — Shift & Certification Lookup.

Provides a filtered view of the technician workforce, allowing the ETL
pipeline to find an available, certified technician for a given work
order. Uses an in-memory roster as a stand-in for a full HR system.
"""

import random
from fastapi import APIRouter, Depends, HTTPException
from api.auth import require_internal_or_roles
from typing import Optional

# The ETL pipeline (etl.extract.get_technician) needs to look up on-shift
# technicians too, and it has no human role to present. require_internal_or_roles
# (unlike require_internal_or_user) keeps the same role restriction for
# human callers — it only adds an internal-service path alongside it.
router = APIRouter(
    prefix="/api/v1/hr/technicians",
    tags=["HR"],
    dependencies=[Depends(require_internal_or_roles("technician", "engineer", "executive", "supervisor"))],
)

_TECHNICIAN_NAMES = [
    "Alice W.",
    "Bob M.",
    "Clara J.",
    "Daniel K.",
    "Eva L.",
    "Frank N.",
    "Grace P.",
    "Henry R.",
    "Isabelle S.",
    "Jason T.",
    "Karen U.",
    "Leo V.",
    "Mia W.",
    "Noah X.",
    "Olivia Y.",
    "Paul Z.",
    "Quinn A.",
    "Rosa B.",
    "Samuel C.",
    "Tasha D.",
]

_CERT_SETS = [
    ["PUMP_SEAL", "HIGH_VOLTAGE"],
    ["PUMP_SEAL"],
    ["ELECTRICAL"],
    ["MECHANICAL", "PUMP_SEAL"],
    ["CONTROL_SYSTEMS"],
    ["HYDRAULICS"],
    ["ROTATING_EQUIPMENT"],
    ["HVAC"],
    ["HVAC", "MECHANICAL"],
    ["GENERAL_MAINTENANCE"],
]


def _generate_technicians():
    rng = random.Random(20260916)
    technicians = []
    for index, name in enumerate(_TECHNICIAN_NAMES, start=101):
        if index == 103:
            certs = ["HVAC", "MECHANICAL"]
        elif index == 107:
            certs = ["HVAC"]
        elif index == 109:
            certs = ["GENERAL_MAINTENANCE"]
        else:
            certs = rng.choice(_CERT_SETS)

        technicians.append(
            {
                "id": f"TECH-{index}",
                "name": name,
                "on_shift": index % 2 == 1,
                "certs": certs,
                # Demo phone numbers (deterministic, not random, so the
                # SMS dispatch flow has a stable recipient across
                # restarts) and a fixed subset flagged as feature-phone
                # users for the SMS-reply path (Build Plan Phase 3) —
                # every technician whose index ends in 5 or 9.
                "phone_number": f"+2547{index:04d}00",
                "non_smartphone": index % 5 in (0, 4),
            }
        )
    return technicians


TECHNICIANS = _generate_technicians()
TECHNICIANS_BY_ID = {tech["id"]: tech for tech in TECHNICIANS}


def get_technician_by_id(technician_id: str) -> dict | None:
    """Look up a technician's full record (phone, cert, shift) by id.

    Used by the dispatch-notification task, which only has
    ``technician_id`` off the ``WorkOrderRecord`` row.
    """
    return TECHNICIANS_BY_ID.get(technician_id)


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
