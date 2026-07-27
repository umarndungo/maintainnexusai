"""
Great Expectations validation helpers for incoming maintenance alerts.

This module defines a lightweight validation suite that rejects malformed
alerts, bad telemetry values, and future timestamps before the ETL pipeline
processes them.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None

    try:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def validate_telemetry_data(telemetry: dict[str, Any] | None) -> bool:
    """Validate raw telemetry data before risk scoring and alert generation."""
    if telemetry is None:
        logger.warning("Telemetry validation failed: missing telemetry payload")
        return False

    if not isinstance(telemetry, dict):
        logger.warning(
            "Telemetry validation failed: expected dict, got %s",
            type(telemetry).__name__,
        )
        return False

    if not telemetry.get("equipment_id"):
        logger.warning("Telemetry validation failed: missing equipment_id")
        return False

    timestamp = _parse_timestamp(telemetry.get("timestamp"))
    if timestamp is None:
        logger.warning("Telemetry validation failed: timestamp is missing or invalid")
        return False

    if timestamp > datetime.now(timezone.utc):
        logger.warning(
            "Telemetry validation failed: timestamp is in the future: %s",
            timestamp.isoformat(),
        )
        return False

    for field in ("temperature", "vibration", "installation_age_hours"):
        if telemetry.get(field) is None:
            logger.warning("Telemetry validation failed: missing %s", field)
            return False

        try:
            numeric = float(telemetry[field])
        except (TypeError, ValueError):
            logger.warning("Telemetry validation failed: %s is not numeric: %s", field, telemetry[field])
            return False

        if numeric < 0:
            logger.warning("Telemetry validation failed: %s must not be negative: %s", field, numeric)
            return False

    return True


def _validate_telemetry(alert: dict[str, Any]) -> bool:
    telemetry = alert.get("telemetry")
    if telemetry is None:
        return True

    return validate_telemetry_data(telemetry)


def validate_alert_with_great_expectations(alert: dict[str, Any]) -> bool:
    """Validate a maintenance alert using lightweight checks.

    The legacy path referenced Great Expectations, but the installed GE
    version in this environment no longer exposes a PandasDataset import.
    We preserve the original validation rules with explicit Python checks.
    """
    if not isinstance(alert, dict):
        logger.warning("Alert validation failed: payload is not a dict")
        return False

    required_fields = ["equipment_id", "part_number", "severity"]
    for field in required_fields:
        if not alert.get(field):
            logger.warning(
                "Alert validation failed: missing or empty %s", field
            )
            return False

    if alert.get("severity") not in ["HIGH", "CRITICAL", "MEDIUM"]:
        logger.warning(
            "Great Expectations validation failed: severity not in allowed set"
        )
        return False

    risk_probability = alert.get("risk_probability")
    if risk_probability is not None:
        try:
            value = float(risk_probability)
        except (TypeError, ValueError):
            logger.warning("risk_probability is not numeric: %s", risk_probability)
            return False

        if not (0.0 <= value <= 1.0):
            logger.warning(
                "risk_probability must be between 0 and 1: %s",
                value,
            )
            return False

    return _validate_telemetry(alert)
