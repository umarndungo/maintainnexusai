"""Rules-based explainability engine for predictive maintenance.

Maps sensor patterns and model outputs to human-readable failure modes,
evidence, and recommended inspections.  All thresholds are derived from
the synthetic telemetry distributions in ``generate_synthetic_operational_data``
and the trained model's feature importance ranking.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Thresholds — one dict per equipment type.
# Keys match the model-feature names in ``model_metadata.json``.
# Values are *alert* thresholds: when exceeded they become evidence.
# ---------------------------------------------------------------------------

thresholds: dict[str, dict[str, dict[str, float]]] = {
    "PUMP": {
        "vibration_mm_s":              {"high": 4.5, "critical": 7.0},
        "temperature_c":               {"high": 75,  "critical": 90},
        "pressure_bar":                {"low": 10.5, "critical_low": 9.0},
        "motor_current_a":             {"high": 90,  "critical": 100},
        "flow_rate_m3h":               {"low": 200000, "critical_low": 170000},
        "vibration_mm_s_rolling_mean_5":  {"high": 4.0},
        "vibration_mm_s_rolling_mean_15": {"high": 3.8},
        "temperature_c_rolling_mean_5":   {"high": 72},
        "temperature_c_rolling_mean_60":  {"high": 68},
        "pressure_bar_rolling_mean_5":    {"low": 10.8},
        "motor_current_a_rolling_mean_5": {"high": 88},
    },
    "LOADING_ARM": {
        "vibration_mm_s":              {"high": 3.0, "critical": 4.5},
        "temperature_c":               {"high": 58,  "critical": 68},
        "pressure_bar":                {"low": 5.8,  "critical_low": 5.0},
        "motor_current_a":             {"high": 28,  "critical": 32},
        "flow_rate_m3h":               {"low": 155000, "critical_low": 140000},
        "valve_position_pct":          {"low": 85, "critical_low": 75},
        "vibration_mm_s_rolling_mean_5":  {"high": 2.8},
        "temperature_c_rolling_mean_5":   {"high": 55},
    },
    "VALVE": {
        "vibration_mm_s":              {"high": 1.5, "critical": 2.5},
        "temperature_c":               {"high": 50,  "critical": 58},
        "pressure_bar":                {"low": 7.5,  "critical_low": 6.5},
        "motor_current_a":             {"high": 15,  "critical": 18},
        "valve_position_pct":          {"low": 80, "critical_low": 65},
        "vibration_mm_s_rolling_mean_5":  {"high": 1.3},
        "temperature_c_rolling_mean_5":   {"high": 48},
    },
}


# ---------------------------------------------------------------------------
# Failure-mode definitions per equipment type.
# Each entry: (mode_name, required_evidence_keys, inspections)
# ``required_evidence_keys`` are the thresholds-dict keys that must fire
# for this mode to be considered *possible*.
# ---------------------------------------------------------------------------

FAILURE_MODES: dict[str, list[dict[str, Any]]] = {
    "PUMP": [
        {
            "name": "Bearing degradation",
            "evidence_keys": ["vibration_mm_s", "vibration_mm_s_rolling_mean_5",
                              "vibration_mm_s_rolling_mean_15", "temperature_c",
                              "temperature_c_rolling_mean_5"],
            "inspections": [
                "Check bearing vibration spectrum",
                "Inspect lubrication condition",
                "Verify operating temperature",
            ],
        },
        {
            "name": "Seal failure / leakage",
            "evidence_keys": ["pressure_bar", "pressure_bar_rolling_mean_5",
                              "flow_rate_m3h"],
            "inspections": [
                "Inspect mechanical seal for leakage",
                "Check suction and discharge pressures",
                "Verify flow rate against rated capacity",
            ],
        },
        {
            "name": "Motor overload",
            "evidence_keys": ["motor_current_a", "motor_current_a_rolling_mean_5",
                              "temperature_c"],
            "inspections": [
                "Measure motor current draw",
                "Check motor winding temperature",
                "Inspect electrical connections",
            ],
        },
        {
            "name": "Cavitation / low NPSH",
            "evidence_keys": ["pressure_bar", "flow_rate_m3h",
                              "vibration_mm_s"],
            "inspections": [
                "Check suction pressure and strainer condition",
                "Verify flow rate is within safe operating range",
                "Listen for cavitation noise",
            ],
        },
    ],
    "LOADING_ARM": [
        {
            "name": "Actuator degradation",
            "evidence_keys": ["motor_current_a", "valve_position_pct",
                              "temperature_c"],
            "inspections": [
                "Inspect actuator mechanism",
                "Check actuator air/hydraulic pressure",
                "Verify valve position accuracy",
            ],
        },
        {
            "name": "Joint / seal wear",
            "evidence_keys": ["vibration_mm_s", "vibration_mm_s_rolling_mean_5",
                              "pressure_bar"],
            "inspections": [
                "Inspect swivel joint seals",
                "Check for visible leaks at connections",
                "Verify joint alignment",
            ],
        },
        {
            "name": "Structural fatigue",
            "evidence_keys": ["vibration_mm_s", "vibration_mm_s_rolling_mean_15",
                              "temperature_c"],
            "inspections": [
                "Visual inspection of arm structure",
                "Check pivot pin wear",
                "Inspect for cracks at stress points",
            ],
        },
    ],
    "VALVE": [
        {
            "name": "Actuator failure",
            "evidence_keys": ["motor_current_a", "valve_position_pct",
                              "temperature_c"],
            "inspections": [
                "Check actuator response time",
                "Inspect actuator diaphragm or piston",
                "Verify control signal wiring",
            ],
        },
        {
            "name": "Seat / disc erosion",
            "evidence_keys": ["pressure_bar", "flow_rate_m3h",
                              "vibration_mm_s"],
            "inspections": [
                "Inspect valve seat for erosion",
                "Check for internal leakage (passing)",
                "Verify shutoff integrity",
            ],
        },
        {
            "name": "Stem packing failure",
            "evidence_keys": ["vibration_mm_s", "motor_current_a",
                              "temperature_c"],
            "inspections": [
                "Inspect stem packing for leakage",
                "Check stem friction / operating torque",
                "Tighten or replace packing rings",
            ],
        },
    ],
}


# ---------------------------------------------------------------------------
# Anomaly score helpers
# ---------------------------------------------------------------------------

def _compute_anomaly_score(
    telemetry: dict[str, Any],
    equipment_type: str,
) -> float:
    """Produce a 0-1 anomaly score from how far sensors deviate from
    their expected baselines.  Each contributing sensor is normalised
    to [0, 1] and the result is the weighted mean.
    """
    type_thresholds = thresholds.get(equipment_type, {})
    scores: list[float] = []

    sensor_weights = {
        "vibration_mm_s": 0.25,
        "temperature_c": 0.20,
        "pressure_bar": 0.20,
        "motor_current_a": 0.15,
        "flow_rate_m3h": 0.10,
        "valve_position_pct": 0.10,
    }

    for sensor, weight in sensor_weights.items():
        value = telemetry.get(sensor)
        if value is None:
            continue
        t = type_thresholds.get(sensor)
        if t is None:
            continue

        critical = t.get("critical") or t.get("critical_low")
        if critical is None:
            continue

        if "low" in t:
            baseline = t["low"]
            if baseline == 0:
                continue
            deviation = max(0.0, (baseline - value) / baseline)
            critical_deviation = max(0.0, (baseline - critical) / baseline) or 1.0
        else:
            baseline = t["high"]
            if baseline == 0:
                continue
            deviation = max(0.0, (value - baseline) / baseline)
            critical_deviation = max(0.0, (critical - baseline) / baseline) or 1.0

        normalised = min(1.0, deviation / critical_deviation)
        scores.append((normalised, weight))

    if not scores:
        return 0.0

    total_weight = sum(w for _, w in scores)
    return round(sum(s * w for s, w in scores) / total_weight, 4)


# ---------------------------------------------------------------------------
# Evidence builder
# ---------------------------------------------------------------------------

def _collect_evidence(
    telemetry: dict[str, Any],
    equipment_type: str,
) -> dict[str, list[str]]:
    """Walk every threshold and collect human-readable evidence strings.
    Returns ``{ sensor_key: [evidence_strings] }``.
    """
    type_thresholds = thresholds.get(equipment_type, {})
    evidence_map: dict[str, list[str]] = {}

    label_map = {
        "vibration_mm_s": "Vibration",
        "vibration_mm_s_rolling_mean_5": "Short-term vibration trend",
        "vibration_mm_s_rolling_mean_15": "Medium-term vibration trend",
        "temperature_c": "Temperature",
        "temperature_c_rolling_mean_5": "Short-term temperature trend",
        "temperature_c_rolling_mean_60": "Long-term temperature trend",
        "pressure_bar": "Pressure",
        "pressure_bar_rolling_mean_5": "Short-term pressure trend",
        "motor_current_a": "Motor current",
        "motor_current_a_rolling_mean_5": "Short-term current trend",
        "flow_rate_m3h": "Flow rate",
        "valve_position_pct": "Valve position",
    }

    for sensor, limits in type_thresholds.items():
        value = telemetry.get(sensor)
        if value is None:
            continue

        label = label_map.get(sensor, sensor)
        entries: list[str] = []

        if "critical" in limits and value >= limits["critical"]:
            entries.append(f"CRITICAL: {label} ({value:.1f}) exceeds {limits['critical']:.1f}")
        elif "high" in limits and value >= limits["high"]:
            entries.append(f"Elevated {label} ({value:.1f}) above {limits['high']:.1f} threshold")

        if "critical_low" in limits and value <= limits["critical_low"]:
            entries.append(f"CRITICAL: {label} ({value:.1f}) below {limits['critical_low']:.1f}")
        elif "low" in limits and value <= limits["low"]:
            entries.append(f"Low {label} ({value:.1f}) below {limits['low']:.1f} threshold")

        if entries:
            evidence_map[sensor] = entries

    return evidence_map


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def explain_prediction(
    telemetry: dict[str, Any],
    equipment_type: str,
    risk_score: float,
) -> dict[str, Any]:
    """Build the explainability payload for a single prediction.

    Parameters
    ----------
    telemetry:
        The raw feature dict passed to the model (must include
        equipment-type keys like ``vibration_mm_s``, ``temperature_c``, etc.).
    equipment_type:
        ``PUMP``, ``LOADING_ARM``, or ``VALVE``.
    risk_score:
        The model's failure probability (0-1).

    Returns
    -------
    dict with ``anomaly_score``, ``likely_failure_modes``,
    ``recommended_inspection``, and ``requires_technician_review``.
    """
    evidence_map = _collect_evidence(telemetry, equipment_type)
    anomaly_score = _compute_anomaly_score(telemetry, equipment_type)

    modes = FAILURE_MODES.get(equipment_type, [])
    likely_failure_modes: list[dict[str, Any]] = []
    all_inspections: list[str] = []

    for mode in modes:
        matched_keys = [k for k in mode["evidence_keys"] if k in evidence_map]
        if not matched_keys:
            continue

        confidence = min(1.0, len(matched_keys) / max(1, len(mode["evidence_keys"])))
        confidence = round(confidence * (0.5 + 0.5 * risk_score), 2)

        mode_evidence: list[str] = []
        for key in matched_keys:
            mode_evidence.extend(evidence_map[key])

        likely_failure_modes.append({
            "name": mode["name"],
            "confidence": confidence,
            "evidence": mode_evidence,
        })

        for insp in mode["inspections"]:
            if insp not in all_inspections:
                all_inspections.append(insp)

    likely_failure_modes.sort(key=lambda m: m["confidence"], reverse=True)

    requires_review = (
        risk_score >= 0.50
        or anomaly_score >= 0.60
        or any(m["confidence"] >= 0.70 for m in likely_failure_modes)
    )

    return {
        "anomaly_score": anomaly_score,
        "likely_failure_modes": likely_failure_modes,
        "recommended_inspection": all_inspections,
        "requires_technician_review": requires_review,
    }
