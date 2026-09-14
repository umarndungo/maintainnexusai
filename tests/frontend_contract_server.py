"""Test-only real API server with isolated persistence and trained-model scoring.

Used by web/scripts/backend-smoke.mjs. Only Celery broker dispatch is replaced;
API handlers, auth, history, model inference and lifecycle writes are real.
"""

import importlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import app
from api.equipment import INVENTORY_DB
from database.auditing import append_audit_log
from database.models import Base
from ml.scoring import METADATA
import tasks


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(engine)
factory = sessionmaker(bind=engine)
for name in ("api.monitoring", "api.maintenance", "api.workorders", "api.technicians", "api.dashboard", "tasks"):
    importlib.import_module(name).SessionLocal = factory
tasks.process_alert.apply_async = lambda **kwargs: None
for part in INVENTORY_DB:
    INVENTORY_DB[part] = 5


def reading(index=60):
    return {"equipment_id": "PUMP-001", "asset_id": "PUMP-001", "station_id": "STATION-1",
            "timestamp": (datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=index)).isoformat(),
            "asset_type": "PUMP", "operating_state": METADATA["categorical_values"]["operating_state"][0],
            "alarm_code": METADATA["categorical_values"]["alarm_code"][0],
            "temperature": 108., "temperature_c": 108., "vibration": 6.4, "vibration_mm_s": 6.4,
            "installation_age_hours": 14500, "pressure_bar": 5., "flow_rate_m3h": 10.,
            "motor_current_a": 2., "valve_position_pct": 50.}


with factory() as db:
    for index in range(60):
        append_audit_log(db, "TELEMETRY_CHECK", {"telemetry": reading(index), "station_id": "STATION-1"})
        db.flush()
    db.commit()


@app.get("/__test/reading", include_in_schema=False)
def sample_reading():
    return reading()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]), log_level="warning")
