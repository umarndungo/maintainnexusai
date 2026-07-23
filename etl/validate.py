"""
Data Validation Module — Quality Rules for Incoming Alerts.

Enforces a set of business rules on alert payloads before they enter
the main pipeline. This gate prevents malformed, incomplete, or
unexpected records from wasting downstream resources.
"""


def validate_alert_data(alert: dict) -> bool:
    """
    Check that an alert dictionary satisfies minimum quality criteria.

    Rules enforced
    --------------
    1. All required keys (``equipment_id``, ``part_number``, ``severity``)
       must be present and **truthy** (not None / empty string).
    2. ``severity`` must be one of ``HIGH``, ``CRITICAL``, or ``MEDIUM``.

    Parameters
    ----------
    alert : dict
        The raw alert payload ingested from the maintenance gateway.

    Returns
    -------
    bool
        ``True`` if the alert passes every rule, ``False`` otherwise.
    """
    # --- Rule 1: Required fields exist and are non-empty ---
    required_keys = ["equipment_id", "part_number", "severity"]
    if not all(k in alert and alert[k] for k in required_keys):
        return False

    # --- Rule 2: Severity must be a recognised level ---
    if alert.get("severity") not in ["HIGH", "CRITICAL", "MEDIUM"]:
        return False

    return True
