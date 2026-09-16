"""Tests for unifying the login identity space with the HR technician
roster (api/technicians.py) so a login actually resolves to a specific
assigned_technician_id — see api/auth.py's _lookup_user().
"""

import asyncio

import bcrypt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import api.auth as auth
from database.models import Base, StaffCredential

USERS = auth.USERS
LoginRequest = auth.LoginRequest


@pytest.fixture(autouse=True)
def credential_database(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as db:
        for user_id, password, role, technician_id in (
            ("tech-demo", "TechDemo-2026", "technician", "TECH-101"),
            ("TECH-105", "Tech-105-2026", "technician", "TECH-105"),
        ):
            db.add(
                StaffCredential(
                    user_id=user_id,
                    password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
                    role=role,
                    technician_id=technician_id,
                )
            )
        db.commit()
    monkeypatch.setattr(auth, "SessionLocal", session_factory)


def test_tech_demo_is_scoped_to_a_roster_technician_id():
    assert USERS["tech-demo"]["technician_id"] == "TECH-101"

    result = asyncio.run(auth.login(LoginRequest(user_id="tech-demo", password="TechDemo-2026")))

    assert result["user"]["role"] == "technician"
    assert result["user"]["technician_id"] == "TECH-101"


def test_raw_roster_id_can_log_in_directly():
    result = asyncio.run(auth.login(LoginRequest(user_id="TECH-105", password="Tech-105-2026")))

    assert result["user"]["id"] == "TECH-105"
    assert result["user"]["role"] == "technician"
    assert result["user"]["technician_id"] == "TECH-105"
    assert "access_token" in result


def test_unknown_id_is_still_rejected():
    from fastapi import HTTPException

    import pytest

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth.login(LoginRequest(user_id="TECH-999", password="Tech-999-2026")))
    assert exc_info.value.status_code == 401
