"""
Model scoring for predictive maintenance telemetry.

This module simulates a risk score for failure within the next 48 hours.
A real implementation would load a trained model artifact and perform
inference on the telemetry payload.
"""

import math
from typing import Any, Dict


def score_telemetry(telemetry: Dict[str, Any]) -> float:
    """Score telemetry data and return a failure probability."""
    temperature = float(telemetry.get("temperature", 0.0))
    vibration = float(telemetry.get("vibration", 0.0))
    installation_age_hours = float(telemetry.get("installation_age_hours", 0.0))

    # Synthetic risk function that mimics a trained classifier.
    score = -8.0 + 0.07 * temperature + 0.9 * vibration + 0.00018 * installation_age_hours
    probability = 1.0 / (1.0 + math.exp(-score))
    return max(0.0, min(1.0, round(probability, 4)))
