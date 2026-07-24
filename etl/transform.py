"""
Data Transformation Module — Business Logic Layer.

Assembles a fully-formed work-order payload by combining validated alert
data with the assigned technician record. This is the "T" in the ETL
pipeline and is the single place where the work-order schema is built.
"""


def build_work_order_payload(alert: dict, technician: dict) -> dict:
    """
    Merge an equipment alert with a technician assignment into a
    work-order creation payload.

    The resulting dictionary is ready to be POSTed to the work-orders API.

    Parameters
    ----------
    alert : dict
        Validated alert payload containing at least ``equipment_id`` and
        ``part_number`` keys.
    technician : dict
        Technician record containing at minimum an ``id`` field.

    Returns
    -------
    dict
        A work-order payload with keys:
            - equipment_id   : asset needing repair
            - technician_id  : assigned technician
            - part_number    : replacement part
            - status         : initial lifecycle state (``"CREATED"``)
            - alert_task_id  : optional upstream alert ID for correlation with the originating alert
    """
    work_order = {
        "equipment_id": alert["equipment_id"],
        "technician_id": technician["id"],
        "part_number": alert["part_number"],
        "status": "CREATED",  # initial state before dispatch
    }

    if alert.get("risk_probability") is not None:
        work_order["risk_probability"] = alert["risk_probability"]
    if alert.get("triggered_by_model") is not None:
        work_order["triggered_by_model"] = alert["triggered_by_model"]
    if alert.get("model_version") is not None:
        work_order["model_version"] = alert["model_version"]
    if alert.get("task_id") is not None:
        work_order["alert_task_id"] = alert["task_id"]

    return work_order
