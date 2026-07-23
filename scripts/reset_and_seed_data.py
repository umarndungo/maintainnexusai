"""Reset the local database and seed unique alerts and work orders."""

import json
import random
import uuid
from datetime import datetime, timezone

from database.db import SessionLocal, engine
from database.models import Base, AuditLog, WorkOrderRecord

PARTS = [
    "Pump Seal Kit #A4",
    "Gasket Set #B2",
    "Valve Seat #C7",
    "Bearing Ring #D5",
    "Control Module #E1",
]

TECHNICIANS = [
    "TECH-101",
    "TECH-102",
    "TECH-103",
    "TECH-104",
    "TECH-105",
]

SEVERITY_OPTIONS = ["HIGH", "CRITICAL", "MEDIUM"]
FAILURE_CODES = [
    "ERR_SEAL_LEAK",
    "ERR_BEARING_WEAR",
    "ERR_OVERHEAT",
    "ERR_ELECTRICAL",
    "ERR_GENERAL",
]


def reset_database() -> None:
    """Empty the current work orders and alert audit log tables."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(AuditLog).delete()
        db.query(WorkOrderRecord).delete()
        db.commit()
    finally:
        db.close()


def seed_alerts_and_work_orders(count: int = 5) -> None:
    """Seed unique alerts and work orders into the local database."""
    db = SessionLocal()
    try:
        for index in range(1, count + 1):
            task_id = str(uuid.uuid4())
            equipment_id = f"EQ-{random.randint(1000, 9999)}"
            part_number = random.choice(PARTS)
            severity = random.choice(SEVERITY_OPTIONS)
            failure_code = random.choice(FAILURE_CODES)

            alert_payload = {
                "task_id": task_id,
                "equipment_id": equipment_id,
                "part_number": part_number,
                "severity": severity,
                "failure_code": failure_code,
            }

            db.add(
                AuditLog(
                    event_name="ALERT_RECEIVED",
                    payload=json.dumps(alert_payload),
                    timestamp=datetime.now(timezone.utc),
                )
            )

            work_order_id = f"WO-{uuid.uuid4().hex[:8].upper()}"
            technician_id = random.choice(TECHNICIANS)
            db.add(
                WorkOrderRecord(
                    id=work_order_id,
                    equipment_id=equipment_id,
                    technician_id=technician_id,
                    part_number=part_number,
                    status="DISPATCHED",
                    created_at=datetime.now(timezone.utc),
                )
            )

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    reset_database()
    seed_alerts_and_work_orders()
    print("Database reset complete.")
    print("Seeded unique alerts and work orders.")
