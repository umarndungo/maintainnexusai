"""
Data Validation Module — Quality Rules for Incoming Alerts.

Enforces a set of business rules on alert payloads before they enter
the main pipeline. This gate prevents malformed, incomplete, or
unexpected records from wasting downstream resources.
"""

import logging

from etl.ge_validation import validate_alert_with_great_expectations

logger = logging.getLogger(__name__)


def validate_alert_data(alert: dict) -> bool:
    """
    Check that an alert dictionary satisfies minimum quality criteria.

    Rules enforced
    --------------
    1. All required keys (``equipment_id``, ``part_number``, ``severity``)
       must be present and **truthy** (not None / empty string).
    2. ``severity`` must be one of ``HIGH``, ``CRITICAL``, or ``MEDIUM``.
    3. ``risk_probability`` values must be numeric and between 0 and 1.
    4. ``telemetry`` values must not contain future timestamps or negative readings.

    Parameters
    ----------
    alert : dict
        The raw alert payload ingested from the maintenance gateway.

    Returns
    -------
    bool
        ``True`` if the alert passes every rule, ``False`` otherwise.
    """
    if not validate_alert_with_great_expectations(alert):
        logger.warning(
            "Great Expectations failed for alert %s",
            alert.get("task_id", "N/A"),
        )
        return False

    required_keys = ["equipment_id", "part_number", "severity"]
    if not all(k in alert and alert[k] for k in required_keys):
        logger.warning(
            "Alert missing required fields: %s",
            [k for k in required_keys if not alert.get(k)],
        )
        return False

    if alert.get("severity") not in ["HIGH", "CRITICAL", "MEDIUM"]:
        logger.warning(
            "Alert has invalid severity: %s",
            alert.get("severity"),
        )
        return False

    return True
