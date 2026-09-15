"""
Equipment Inventory Module — Mock Warehouse Stock API.

Provides a single read-only endpoint to check current inventory levels
for a given replacement part. Uses an in-memory dictionary as a stand-in
for a real warehouse management system database.
"""

import random
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from api.auth import require_roles

router = APIRouter(
    prefix="/api/v1/warehouse",
    tags=["Inventory"],
    dependencies=[Depends(require_roles("technician", "engineer", "executive", "supervisor"))],
)

_PARTS = [
    "Pump Seal Kit #A4",
    "Pump Seal Kit #A1",
    "Pump Seal Kit #A3",
    "Pump Seal Kit #A2",
    "Gasket Set #B2",
    "Gasket Set #B1",
    "Gasket Set #B3",
    "Gasket Set #B4",
    "Control Valve #C8",
    "Control Valve #C1",
    "Control Valve #C3",
    "Control Valve #C4",
    "Bearing Ring #D5",
    "Sensor Module #E1",
    "Actuator Assembly #F2",
    "Filter Cartridge #G7",
    "Circuit Board #H4",
    "Relay Module #J3",
    "Pressure Transducer #K1",
    "Hydraulic Hose #L6",
]

PARTS = _PARTS

# Prefix -> numeric-suffix range. Each maps to one of the ML model's 3
# trained asset_type categories via etl.telemetry._ASSET_TYPES_BY_PREFIX
# (PUMP/MOTOR/COMP -> PUMP, SENSOR/CTRL -> LOADING_ARM, VALVE -> VALVE,
# ARM -> LOADING_ARM directly, no indirection).
_EQUIPMENT_PREFIX_RANGES = (
    ("PUMP", 100),
    ("VALVE", 200),
    ("MOTOR", 300),
    ("COMP", 400),
    ("SENSOR", 500),
    ("CTRL", 600),
    ("ARM", 700),
)


def _generate_equipment_fleet() -> list[str]:
    """Randomize the equipment fleet once per process start — a fixed-size
    pool (2-5 assets per prefix) so equipment-monitoring history stays
    coherent for the life of a run, but the fleet itself differs between
    restarts/deployments rather than being a hardcoded list. Every
    category the model was trained on (PUMP, VALVE, LOADING_ARM) is
    guaranteed present every run."""
    fleet: list[str] = []
    for prefix, base in _EQUIPMENT_PREFIX_RANGES:
        count = random.randint(2, 5)
        suffixes = random.sample(range(1, 100), count)  # no duplicate suffix within a prefix
        fleet.extend(f"{prefix}-{base + suffix}" for suffix in suffixes)
    return fleet


EQUIPMENT_IDS = _generate_equipment_fleet()

# In-memory inventory store — maps part names to on-hand quantities.
# In production this would query an ERP or WMS database.
INVENTORY_DB = {
    part: random.randint(0, 25)
    for part in _PARTS
}


@router.get("/stock")
async def check_stock(
    part_number: Annotated[str, Query(...)]
):
    """
    Return current stock level for a requested part number.

    Query Parameters
    ----------------
    part_number : str
        The unique identifier / name of the part to look up.

    Returns
    -------
    dict
        - part_number       : the queried part identifier
        - in_stock           : boolean availability flag
        - quantity_available : number of units on hand (0 if absent)
    """
    qty = INVENTORY_DB.get(part_number, 0)
    return {
        "part_number": part_number,
        "in_stock": qty > 0,
        "quantity_available": qty,
    }
