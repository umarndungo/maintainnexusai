"""Internal client for the notifications service contract — mirrors
etl/ml_client.py's shape. Celery calls these instead of importing the
Africa's Talking / Firebase SDKs directly, keeping "one call site per
provider" true (06-INTEGRATIONS-GUIDE.md §2)."""

import requests

from config import API_INTERNAL_BASE_URL, INTERNAL_SERVICE_TOKEN

BASE_URL = API_INTERNAL_BASE_URL
_HEADERS = {"X-Internal-Service": INTERNAL_SERVICE_TOKEN}


def send_sms(recipient: str, message: str, work_order_id: str | None = None) -> dict | None:
    try:
        response = requests.post(
            f"{BASE_URL}/notifications/sms",
            json={"recipient": recipient, "message": message, "work_order_id": work_order_id},
            headers=_HEADERS,
            timeout=10,
        )
    except requests.RequestException:
        return None
    return response.json() if response.status_code == 202 else None


def send_push(device_token: str, title: str, body: str, data: dict | None = None, work_order_id: str | None = None) -> dict | None:
    try:
        response = requests.post(
            f"{BASE_URL}/notifications/push",
            json={"device_token": device_token, "title": title, "body": body, "data": data or {}, "work_order_id": work_order_id},
            headers=_HEADERS,
            timeout=10,
        )
    except requests.RequestException:
        return None
    return response.json() if response.status_code == 202 else None
