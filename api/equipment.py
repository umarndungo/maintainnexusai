"""
Equipment Inventory Module — Mock Warehouse Stock API.

Provides a single read-only endpoint to check current inventory levels
for a given replacement part. Uses an in-memory dictionary as a stand-in
for a real warehouse management system database.
"""

import random
from typing import Annotated

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/v1/warehouse", tags=["Inventory"])

_PARTS = [
    "Pump Seal Kit #A4",
    "Gasket Set #B2",
    "Control Valve #C8",
    "Bearing Ring #D5",
    "Sensor Module #E1",
]

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
