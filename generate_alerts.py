"""
Script to generate and send fake maintenance alerts to the local API.

This helper is useful for manual testing and local development when you
need sample alert traffic without connecting real equipment.
"""

import random
import requests
from faker import Faker

from api.equipment import EQUIPMENT_IDS, PARTS

fake = Faker()

severity_choices = ["HIGH", "CRITICAL", "MEDIUM"]
failure_codes = [
    "ERR_SEAL_LEAK",
    "ERR_BEARING_WEAR",
    "ERR_OVERHEAT",
    "ERR_ELECTRICAL",
    "ERR_GENERAL",
]

for _ in range(10):
    payload = {
        "equipment_id": random.choice(EQUIPMENT_IDS),
        "part_number": random.choice(PARTS),
        "severity": random.choice(severity_choices),
        "failure_code": random.choice(failure_codes),
    }

    response = requests.post(
        "http://localhost:8000/api/v1/alerts/maintenance",
        json=payload,
        timeout=5,
    )

    print(response.status_code)
    print(response.json())