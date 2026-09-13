"""Internal client for the ML risk-scoring service contract."""

import requests
from config import API_INTERNAL_BASE_URL, INTERNAL_SERVICE_TOKEN

BASE_URL = API_INTERNAL_BASE_URL


def predict_risk(telemetry: dict) -> dict | None:
    response = requests.post(
        f"{BASE_URL}/ml/predict-risk",
        json=telemetry,
        headers={"X-Internal-Service": INTERNAL_SERVICE_TOKEN},
        timeout=10,
    )
    if response.status_code != 200:
        return None
    return response.json()