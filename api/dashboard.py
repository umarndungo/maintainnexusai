"""
Dashboard Summary Module — Aggregated backend data for the UI.

Provides a single endpoint that returns work order counts, alert counts,
available on-shift technicians, and current inventory levels.
"""

from fastapi import APIRouter, status

from api.equipment import INVENTORY_DB
from api.technicians import TECHNICIANS
from database.db import SessionLocal
from database.models import AuditLog, WorkOrderRecord

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/summary", status_code=status.HTTP_200_OK)
async def get_dashboard_summary():
    """
    Return aggregated dashboard data for the Flutter UI.

    Returns
    -------
    dict
        - work_order_count      : total dispatched work orders
        - alert_count           : total received alert events
        - available_technicians : currently on-shift technician roster
        - inventory             : current part availability for the warehouse
    """
    db = SessionLocal()
    try:
        work_order_count = db.query(WorkOrderRecord).count()
        alert_count = (
            db.query(AuditLog)
            .filter(AuditLog.event_name == "ALERT_RECEIVED")
            .count()
        )
    finally:
        db.close()

    technicians = [
        {
            "id": tech["id"],
            "name": tech["name"],
            "certs": tech["certs"],
        }
        for tech in TECHNICIANS
        if tech["on_shift"]
    ]

    inventory = [
        {
            "part_number": part,
            "quantity_available": qty,
            "in_stock": qty > 0,
        }
        for part, qty in INVENTORY_DB.items()
    ]

    return {
        "work_order_count": work_order_count,
        "alert_count": alert_count,
        "available_technicians": technicians,
        "inventory": inventory,
    }
