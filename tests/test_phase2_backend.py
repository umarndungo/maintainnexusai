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
    require_internal_or_roles,
    require_internal_service,
    require_roles,
)
from api.ml import RiskRequest, predict_risk as predict_risk_endpoint
from database.auditing import append_audit_log
from database.lifecycle import append_lifecycle_event, current_work_order_status
from database.models import AuditLog, Base
from etl.load import dispatch_work_order
from etl.ml_client import predict_risk


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


def test_internal_or_roles_accepts_internal_token_or_matching_role():
    """api/equipment.py's /warehouse/stock and api/technicians.py's
    /hr/technicians/available both moved from require_roles to this —
    an unattended ETL caller (no user session) now has a path in, without
    loosening the existing human role restriction (unlike
    require_internal_or_user, which drops the role check for any
    logged-in user)."""
    from config import INTERNAL_SERVICE_TOKEN

    require_engineer_or_internal = require_internal_or_roles("engineer", "supervisor")

    internal_user = require_engineer_or_internal(x_internal_service=INTERNAL_SERVICE_TOKEN, credentials=None)
    assert internal_user["role"] == "internal"

    token = create_access_token("engineer-demo")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    human_user = require_engineer_or_internal(x_internal_service=None, credentials=creds)
    assert human_user["id"] == "engineer-demo"

    tech_token = create_access_token("tech-demo")
    tech_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=tech_token)
    with pytest.raises(HTTPException) as error:
        require_engineer_or_internal(x_internal_service=None, credentials=tech_creds)
    assert error.value.status_code == 403

    with pytest.raises(HTTPException) as error:
        require_engineer_or_internal(x_internal_service=None, credentials=None)
    assert error.value.status_code == 401


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


def test_ml_client_uses_internal_service_contract():
    response = type(
        "Response",
        (),
        {"status_code": 200, "json": lambda self: {"risk_score": 0.91}},
    )()
    with patch("etl.ml_client.requests.post", return_value=response) as request:
        result = predict_risk({"equipment_id": "PUMP-1", "equipment_type": "PUMP"})

    assert result["risk_score"] == 0.91
    assert request.call_args.kwargs["headers"]["X-Internal-Service"] == "internal-dev-token"


def test_ml_endpoint_maps_model_result_to_shared_contract():
    with patch(
        "api.ml.score_telemetry",
        return_value={
            "failure_probability": 0.91,
            "risk_level": "HIGH",
            "prediction_horizon_hours": 6,
        },
    ):
        import asyncio

        result = asyncio.run(
            predict_risk_endpoint(
                RiskRequest(
                    equipment_id="PUMP-1",
                    equipment_type="PUMP",
                    temperature_c=110.0,
                )
            )
        )

    assert result["risk_score"] == 0.91
    assert result["risk_level"] == "CRITICAL"
    assert result["prediction_horizon_hours"] == 6
    assert result["model_version"].startswith("xgboost-")
    assert result["prediction_id"]


def test_telemetry_endpoint_enqueues_without_scoring():
    from api.maintenance import TelemetryPayload, receive_telemetry

    with patch("api.maintenance._write_audit_log"), patch(
        "tasks.process_telemetry.delay"
    ) as enqueue, patch("etl.ml_client.predict_risk") as score:
        import asyncio

        result = asyncio.run(
            receive_telemetry(
                TelemetryPayload(
                    equipment_id="EQ-1",
                    temperature=90.0,
                    vibration=2.0,
                    installation_age_hours=1000,
                    timestamp="2025-01-01T12:00:00Z",
                )
            )
        )

    assert result["status"] == "queued"
    enqueue.assert_called_once()
    score.assert_not_called()


def test_celery_telemetry_task_scores_and_enqueues_alert():
    from tasks import process_telemetry

    score_result = {"risk_score": 0.92, "risk_level": "HIGH"}
    alert = {
        "task_id": "telemetry-1",
        "equipment_id": "EQ-1",
        "risk_probability": 0.92,
        "risk_level": "HIGH",
    }
    telemetry = {"task_id": "telemetry-1", "equipment_id": "EQ-1"}

    with patch("tasks._write_audit_log"), patch(
        "tasks.process_alert.delay"
    ) as enqueue, patch(
        "etl.telemetry.score_and_decide", return_value=(score_result, alert)
    ) as score:
        result = process_telemetry.run(telemetry)

    assert result == {"status": "queued", "alert_created": True, "task_id": "telemetry-1"}
    score.assert_called_once_with(telemetry)
    enqueue.assert_called_once_with(alert)
