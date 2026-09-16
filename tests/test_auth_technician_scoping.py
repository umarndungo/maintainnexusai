"""Tests for unifying the login identity space with the HR technician
roster (api/technicians.py) so a login actually resolves to a specific
assigned_technician_id — see api/auth.py's _lookup_user().
"""

import asyncio

from api.auth import USERS, LoginRequest, login


def test_tech_demo_is_scoped_to_a_roster_technician_id():
    assert USERS["tech-demo"]["technician_id"] == "TECH-101"

    result = asyncio.run(login(LoginRequest(user_id="tech-demo")))

    assert result["user"]["role"] == "technician"
    assert result["user"]["technician_id"] == "TECH-101"


def test_raw_roster_id_can_log_in_directly():
    result = asyncio.run(login(LoginRequest(user_id="TECH-105")))

    assert result["user"]["id"] == "TECH-105"
    assert result["user"]["role"] == "technician"
    assert result["user"]["technician_id"] == "TECH-105"
    assert "access_token" in result


def test_unknown_id_is_still_rejected():
    from fastapi import HTTPException

    import pytest

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(login(LoginRequest(user_id="TECH-999")))
    assert exc_info.value.status_code == 401
