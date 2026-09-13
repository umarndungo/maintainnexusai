"""Focused tests for the Phase 2 backend contracts."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.auth import (
    create_access_token,
    get_current_user,
    require_internal_service,
    require_roles,
)
from database.auditing import append_audit_log
from database.lifecycle import append_lifecycle_event, current_work_order_status
from database.models import AuditLog, Base
from etl.load import dispatch_work_order


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_access_token_round_trip_preserves_role():
    token = create_access_token("engineer-demo")
    user = get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))

    assert user["id"] == "engineer-demo"
    assert user["role"] == "engineer"
    assert user["station_ids"] == ["STATION-1"]


def test_role_dependency_rejects_wrong_role():
    require_engineer = require_roles("engineer")

    with pytest.raises(HTTPException) as error:
        require_engineer({"role": "technician"})

    assert error.value.status_code == 403


def test_internal_service_requires_exact_token():
    require_internal_service("internal-dev-token")

    with pytest.raises(HTTPException) as error:
        require_internal_service("wrong-token")

    assert error.value.status_code == 403


def test_lifecycle_status_is_derived_and_hash_chained(db_session):
    first = append_lifecycle_event(
        db_session,
        work_order_id="WO-1",
        to_status="PENDING_APPROVAL",
        actor_id="system",
        actor_role="internal",
    )
    db_session.commit()
    second = append_lifecycle_event(
        db_session,
        work_order_id="WO-1",
        from_status="PENDING_APPROVAL",
        to_status="APPROVED",
        actor_id="engineer-demo",
        actor_role="engineer",
    )
    db_session.commit()

    assert current_work_order_status(db_session, "WO-1") == "APPROVED"
    assert first.previous_event_hash == "GENESIS"
    assert second.previous_event_hash == first.event_hash
    assert first.event_hash != second.event_hash


def test_audit_log_rejects_appending_to_unchained_legacy_row(db_session):
    db_session.add(AuditLog(event_name="LEGACY", payload="{}"))
    db_session.commit()

    with pytest.raises(RuntimeError, match="unchained audit log"):
        append_audit_log(db_session, "SECOND", {"value": 2})


def test_dispatch_uses_internal_service_header():
    response = type("Response", (), {"status_code": 201, "json": lambda self: {"work_order_id": "WO-1"}})()
    with patch("etl.load.requests.post", return_value=response) as request:
        result = dispatch_work_order({"equipment_id": "EQ-1"})

    assert result["work_order_id"] == "WO-1"
    assert request.call_args.kwargs["headers"]["X-Internal-Service"] == "internal-dev-token"
