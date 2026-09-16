"""Password login and self-service password change behavior."""

import asyncio

import bcrypt
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import api.auth as auth
from database.models import Base, StaffCredential


@pytest.fixture
def credential_database(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    identities = {
        "TECH-105": ("Tech-105-2026", "technician", "TECH-105"),
        "ENG-1": ("Eng-1-2026", "engineer", None),
        "SUP-1": ("Sup-1-2026", "supervisor", None),
        "EXEC-1": ("Exec-1-2026", "executive", None),
        "tech-demo": ("TechDemo-2026", "technician", "TECH-101"),
        "engineer-demo": ("EngineerDemo-2026", "engineer", None),
        "supervisor-demo": ("SupervisorDemo-2026", "supervisor", None),
        "executive-demo": ("ExecutiveDemo-2026", "executive", None),
    }
    with session_factory() as db:
        for user_id, (password, role, technician_id) in identities.items():
            db.add(
                StaffCredential(
                    user_id=user_id,
                    password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
                    role=role,
                    technician_id=technician_id,
                    must_change_password=True,
                )
            )
        db.commit()
    monkeypatch.setattr(auth, "SessionLocal", session_factory)
    return identities


def test_seeded_technician_login_and_wrong_password(credential_database):
    result = asyncio.run(auth.login(auth.LoginRequest(user_id="TECH-105", password="Tech-105-2026")))

    assert result["user"]["role"] == "technician"
    assert result["user"]["technician_id"] == "TECH-105"
    assert result["user"]["must_change_password"] is True

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth.login(auth.LoginRequest(user_id="TECH-105", password="wrong-password")))
    assert exc_info.value.status_code == 401


@pytest.mark.parametrize(
    ("user_id", "password", "role"),
    [
        ("ENG-1", "Eng-1-2026", "engineer"),
        ("SUP-1", "Sup-1-2026", "supervisor"),
        ("EXEC-1", "Exec-1-2026", "executive"),
        ("tech-demo", "TechDemo-2026", "technician"),
        ("engineer-demo", "EngineerDemo-2026", "engineer"),
        ("supervisor-demo", "SupervisorDemo-2026", "supervisor"),
        ("executive-demo", "ExecutiveDemo-2026", "executive"),
    ],
)
def test_seeded_roles_and_demo_accounts_login(credential_database, user_id, password, role):
    result = asyncio.run(auth.login(auth.LoginRequest(user_id=user_id, password=password)))
    assert result["user"]["role"] == role


def test_change_password_clears_first_login_requirement(credential_database):
    user = {"id": "TECH-105", "role": "technician", "technician_id": "TECH-105"}
    result = asyncio.run(
        auth.change_password(
            auth.ChangePasswordRequest(
                current_password="Tech-105-2026",
                new_password="New-Tech-105-password",
            ),
            user,
        )
    )
    assert result == {"status": "ok"}

    login_result = asyncio.run(
        auth.login(auth.LoginRequest(user_id="TECH-105", password="New-Tech-105-password"))
    )
    assert login_result["user"]["must_change_password"] is False


def test_change_password_rejects_wrong_current_password(credential_database):
    user = {"id": "TECH-105", "role": "technician", "technician_id": "TECH-105"}
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            auth.change_password(
                auth.ChangePasswordRequest(
                    current_password="wrong-password",
                    new_password="New-Tech-105-password",
                ),
                user,
            )
        )
    assert exc_info.value.status_code == 401


def test_change_password_rejects_short_new_password():
    with pytest.raises(ValueError):
        auth.ChangePasswordRequest(current_password="old-password", new_password="short")