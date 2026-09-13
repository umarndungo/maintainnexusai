"""
Telemetry generator for predictive maintenance simulation.

This module produces synthetic equipment telemetry records and converts
high-risk telemetry into an alert payload that can enter the existing
maintenance pipeline.
"""

import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from api.equipment import EQUIPMENT_IDS, PARTS

from etl.ge_validation import validate_telemetry_data
from etl.ml_client import predict_risk
from ml.scoring import FEATURES


def generate_telemetry() -> Dict[str, Any]:
    """Generate a single synthetic telemetry event for one asset."""
    equipment_id = random.choice(EQUIPMENT_IDS)
    temperature = round(random.uniform(60.0, 120.0), 1)
    vibration = round(random.uniform(0.5, 7.5), 2)
    installation_age_hours = random.randint(500, 20000)
    equipment_prefix = equipment_id.split("-")[0]
    asset_type = {
        "VALVE": "VALVE",
        "PUMP": "PUMP",
        "MOTOR": "PUMP",
        "COMP": "PUMP",
        "SENSOR": "LOADING_ARM",
        "CTRL": "LOADING_ARM",
    }.get(equipment_prefix, "PUMP")
    asset_id = f"{asset_type if asset_type != 'LOADING_ARM' else 'ARM'}-{random.randint(1, 12):03d}"
    sensors = {
        "pressure_bar": round(random.uniform(1.0, 12.0), 2),
        "temperature_c": temperature,
        "flow_rate_m3h": round(random.uniform(5.0, 80.0), 2),
        "motor_current_a": round(random.uniform(2.0, 25.0), 2),
        "vibration_mm_s": vibration,
        "valve_position_pct": round(random.uniform(0.0, 100.0), 2),
    }

    telemetry = {
        "equipment_id": equipment_id,
        "temperature": temperature,
        "vibration": vibration,
        "installation_age_hours": installation_age_hours,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "asset_id": asset_id,
        "asset_type": asset_type,
        "operating_state": "RUNNING",
        "alarm_code": "NONE",
    }
    telemetry.update(sensors)
    for name, value in sensors.items():
        telemetry[f"{name}_lag_1"] = value
        telemetry[f"{name}_delta_1"] = 0.0
        for window in (5, 15, 60):
            telemetry[f"{name}_rolling_mean_{window}"] = value
            telemetry[f"{name}_rolling_std_{window}"] = 0.0
    return {key: telemetry[key] for key in set(telemetry) | set(FEATURES) if key in telemetry}


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


def process_raw_telemetry(
    telemetry: Dict[str, Any],
    alert_threshold: float = 0.85,
    model_version: str = "mock-v1",
) -> Dict[str, Any] | None:
    """Validate raw telemetry and build an alert payload only when it qualifies."""
    if not validate_telemetry_data(telemetry):
        return None

    score_result = predict_risk(telemetry)
    if score_result is None:
        return None
    risk_probability = (
        score_result.get("risk_score", 0.0)
        if isinstance(score_result, dict)
        else float(score_result)
    )
    if risk_probability <= alert_threshold:
        return None

    alert_payload = build_alert_from_telemetry(
        telemetry=telemetry,
        risk_probability=risk_probability,
        model_version=score_result.get("model_version", model_version),
    )
    alert_payload["risk_level"] = score_result.get("risk_level")
    alert_payload["top_features"] = score_result.get("top_features", [])
    alert_payload["prediction_id"] = score_result.get("prediction_id")
    alert_payload["task_id"] = str(uuid.uuid4())
    return alert_payload
