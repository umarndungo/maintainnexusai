"""
Telemetry generator for predictive maintenance simulation.

This module produces synthetic equipment telemetry records and converts
high-risk telemetry into an alert payload that can enter the existing
maintenance pipeline.
"""

import random
import uuid
import zlib
from datetime import datetime, timezone
from typing import Any, Dict

from api.equipment import EQUIPMENT_IDS, PARTS

from etl.feature_engineering import engineer_features
from etl.ge_validation import validate_telemetry_data
from etl.ml_client import predict_risk

# Neutral fallback values for sensors a legacy caller (or the public
# ``/alerts/telemetry`` contract) doesn't report. These are only used when
# the field is genuinely absent from the incoming telemetry — real values
# always take precedence. Chosen as the midpoint of the ranges the demo
# generator below samples from.
_SENSOR_DEFAULTS = {
    "pressure_bar": 6.5,
    "flow_rate_m3h": 42.5,
    "motor_current_a": 13.5,
    "valve_position_pct": 50.0,
}

# Must match ml/models/model_metadata.json's trained categorical_values —
# an unrecognised category silently becomes NaN to the model instead of a
# clear error, so these need to stay in sync with the training data.
_ASSET_TYPES_BY_PREFIX = {
    "VALVE": "VALVE",
    "PUMP": "PUMP",
    "MOTOR": "PUMP",
    "COMP": "PUMP",
    "SENSOR": "LOADING_ARM",
    "CTRL": "LOADING_ARM",
}
_OPERATING_STATES = ("LOADING", "IDLE")
_ASSET_ID_BUCKETS = {"VALVE": 24, "PUMP": 12, "LOADING_ARM": 12}


def _infer_asset_type(equipment_id: str) -> str:
    prefix = equipment_id.split("-")[0]
    return _ASSET_TYPES_BY_PREFIX.get(prefix, "PUMP")


def _stable_asset_id(equipment_id: str, asset_type: str) -> str:
    """Deterministically map an equipment_id to a trained asset_id bucket.

    Deterministic (not random) so repeated telemetry for the same physical
    equipment_id keeps landing in the same rolling-history bucket instead of
    scattering its history across unrelated assets on every call.
    """
    bucket_count = _ASSET_ID_BUCKETS.get(asset_type, 12)
    bucket = (zlib.crc32(equipment_id.encode("utf-8")) % bucket_count) + 1
    prefix = "ARM" if asset_type == "LOADING_ARM" else asset_type
    return f"{prefix}-{bucket:03d}"


def _resolve_sensor(telemetry: Dict[str, Any], new_key: str, legacy_key: str | None, default: float) -> float:
    if telemetry.get(new_key) is not None:
        return float(telemetry[new_key])
    if legacy_key and telemetry.get(legacy_key) is not None:
        return float(telemetry[legacy_key])
    return default


def enrich_for_scoring(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """Build the full model-ready feature set from raw/legacy telemetry.

    Fills in ``asset_id``/``asset_type``/``operating_state``/``alarm_code``
    and the six base sensor readings from whatever the caller supplied
    (falling back to legacy ``temperature``/``vibration`` or neutral
    defaults), then computes the real lag/delta/rolling-window features from
    that asset's actual recent history via ``feature_engineering``. Returns a
    new dict — the caller's original telemetry is left untouched.
    """
    equipment_id = telemetry["equipment_id"]
    asset_type = telemetry.get("asset_type") or _infer_asset_type(equipment_id)
    asset_id = telemetry.get("asset_id") or _stable_asset_id(equipment_id, asset_type)
    operating_state = telemetry.get("operating_state") or "LOADING"
    alarm_code = telemetry.get("alarm_code") or "NONE"

    sensors = {
        "pressure_bar": _resolve_sensor(telemetry, "pressure_bar", None, _SENSOR_DEFAULTS["pressure_bar"]),
        "temperature_c": _resolve_sensor(telemetry, "temperature_c", "temperature", 0.0),
        "flow_rate_m3h": _resolve_sensor(telemetry, "flow_rate_m3h", None, _SENSOR_DEFAULTS["flow_rate_m3h"]),
        "motor_current_a": _resolve_sensor(telemetry, "motor_current_a", None, _SENSOR_DEFAULTS["motor_current_a"]),
        "vibration_mm_s": _resolve_sensor(telemetry, "vibration_mm_s", "vibration", 0.0),
        "valve_position_pct": _resolve_sensor(
            telemetry, "valve_position_pct", None, _SENSOR_DEFAULTS["valve_position_pct"]
        ),
    }

    enriched = {
        **telemetry,
        "asset_id": asset_id,
        "asset_type": asset_type,
        "equipment_type": telemetry.get("equipment_type") or asset_type,
        "operating_state": operating_state,
        "alarm_code": alarm_code,
        **sensors,
        **engineer_features(asset_id, sensors),
    }
    return enriched


def generate_telemetry() -> Dict[str, Any]:
    """Generate a single synthetic telemetry event for one asset."""
    equipment_id = random.choice(EQUIPMENT_IDS)
    temperature = round(random.uniform(60.0, 120.0), 1)
    vibration = round(random.uniform(0.5, 7.5), 2)
    installation_age_hours = random.randint(500, 20000)
    asset_type = _infer_asset_type(equipment_id)
    # Unlike enrich_for_scoring's deterministic mapping, the demo generator
    # picks a random asset per run to simulate different equipment reporting
    # over time — its rolling history still accumulates in Redis as the same
    # random IDs recur across scheduled runs.
    bucket_count = _ASSET_ID_BUCKETS.get(asset_type, 12)
    prefix = "ARM" if asset_type == "LOADING_ARM" else asset_type
    asset_id = f"{prefix}-{random.randint(1, bucket_count):03d}"

    telemetry = {
        "equipment_id": equipment_id,
        "temperature": temperature,
        "vibration": vibration,
        "installation_age_hours": installation_age_hours,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "asset_id": asset_id,
        "asset_type": asset_type,
        "operating_state": random.choice(_OPERATING_STATES),
        "alarm_code": "NONE",
        "pressure_bar": round(random.uniform(1.0, 12.0), 2),
        "temperature_c": temperature,
        "flow_rate_m3h": round(random.uniform(5.0, 80.0), 2),
        "motor_current_a": round(random.uniform(2.0, 25.0), 2),
        "vibration_mm_s": vibration,
        "valve_position_pct": round(random.uniform(0.0, 100.0), 2),
    }
    return enrich_for_scoring(telemetry)


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

    # Score using a fully model-featured copy; the alert payload below still
    # carries the caller's original (unenriched) telemetry.
    score_result = predict_risk(enrich_for_scoring(telemetry))
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
