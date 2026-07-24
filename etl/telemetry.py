"""
Telemetry generator for predictive maintenance simulation.

This module produces synthetic equipment telemetry records and converts
high-risk telemetry into an alert payload that can enter the existing
maintenance pipeline.
"""

import random
from datetime import datetime, timezone
from typing import Any, Dict

from api.equipment import EQUIPMENT_IDS, PARTS


def generate_telemetry() -> Dict[str, Any]:
    """Generate a single synthetic telemetry event for one asset."""
    equipment_id = random.choice(EQUIPMENT_IDS)
    temperature = round(random.uniform(60.0, 120.0), 1)
    vibration = round(random.uniform(0.5, 7.5), 2)
    installation_age_hours = random.randint(500, 20000)

    return {
        "equipment_id": equipment_id,
        "temperature": temperature,
        "vibration": vibration,
        "installation_age_hours": installation_age_hours,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def build_alert_from_telemetry(
    telemetry: Dict[str, Any],
    risk_probability: float,
    model_version: str = "mock-v1",
) -> Dict[str, Any]:
    """Build an alert payload from high-risk telemetry."""
    temperature = telemetry.get("temperature", 0.0)
    vibration = telemetry.get("vibration", 0.0)

    if temperature >= 105.0:
        failure_code = "ERR_OVERHEAT"
    elif vibration >= 6.0:
        failure_code = "ERR_VIBRATION"
    elif temperature >= 95.0:
        failure_code = "ERR_SEAL_LEAK"
    else:
        failure_code = "ERR_GENERAL"

    severity = "CRITICAL" if risk_probability >= 0.95 else "HIGH"

    return {
        "equipment_id": telemetry["equipment_id"],
        "part_number": random.choice(PARTS),
        "severity": severity,
        "failure_code": failure_code,
        "risk_probability": round(risk_probability, 3),
        "telemetry": telemetry,
        "triggered_by_model": True,
        "model_version": model_version,
    }
