"""
Unit Tests for the ETL Data Pipeline.

Tests every ETL module in isolation using mocked HTTP responses so the
suite runs fast and without requiring the FastAPI application or a
database to be running.

Run with::

    pytest tests/
"""

import pytest
from unittest.mock import patch, MagicMock

from etl.ge_validation import validate_telemetry_data
from etl.telemetry import process_raw_telemetry
from etl.validate import validate_alert_data
from etl.transform import build_work_order_payload
from etl.extract import check_stock, get_technician, resolve_cert_for_failure
from etl.load import dispatch_work_order
from etl.pipeline import process_alert_pipeline


# =========================================================================
# Tests: validate.py
# =========================================================================

class TestValidateAlertData:
    """Cover valid and invalid alert payloads."""

    def test_valid_alert(self):
        """A well-formed alert with required keys and valid severity."""
        alert = {"equipment_id": "EQ-1", "part_number": "P-100", "severity": "HIGH"}
        assert validate_alert_data(alert) is True

    def test_missing_keys(self):
        """Missing a required key returns False."""
        assert validate_alert_data({"equipment_id": "EQ-1"}) is False

    def test_invalid_severity(self):
        """Unrecognised severity level returns False."""
        alert = {"equipment_id": "EQ-1", "part_number": "P-100", "severity": "LOW"}
        assert validate_alert_data(alert) is False

    def test_empty_values(self):
        """Empty / falsy values for required keys return False."""
        alert = {"equipment_id": "", "part_number": "P-100", "severity": "HIGH"}
        assert validate_alert_data(alert) is False

    def test_none_value(self):
        """None value for a required key returns False."""
        alert = {"equipment_id": None, "part_number": "P-100", "severity": "HIGH"}
        assert validate_alert_data(alert) is False


class TestTelemetryValidation:
    """Cover validation rules for raw telemetry input."""

    def test_valid_telemetry_data(self):
        telemetry = {
            "equipment_id": "EQ-1",
            "temperature": 95.2,
            "vibration": 4.2,
            "installation_age_hours": 1200,
            "timestamp": "2025-01-01T12:00:00Z",
        }
        assert validate_telemetry_data(telemetry) is True

    def test_missing_equipment_id(self):
        telemetry = {
            "temperature": 95.2,
            "vibration": 4.2,
            "installation_age_hours": 1200,
            "timestamp": "2025-01-01T12:00:00Z",
        }
        assert validate_telemetry_data(telemetry) is False

    def test_negative_value_rejected(self):
        telemetry = {
            "equipment_id": "EQ-1",
            "temperature": -5.0,
            "vibration": 4.2,
            "installation_age_hours": 1200,
            "timestamp": "2025-01-01T12:00:00Z",
        }
        assert validate_telemetry_data(telemetry) is False

    def test_invalid_timestamp_rejected(self):
        telemetry = {
            "equipment_id": "EQ-1",
            "temperature": 95.2,
            "vibration": 4.2,
            "installation_age_hours": 1200,
            "timestamp": "not-a-timestamp",
        }
        assert validate_telemetry_data(telemetry) is False

    def test_future_timestamp_rejected(self):
        telemetry = {
            "equipment_id": "EQ-1",
            "temperature": 95.2,
            "vibration": 4.2,
            "installation_age_hours": 1200,
            "timestamp": "2999-01-01T12:00:00Z",
        }
        assert validate_telemetry_data(telemetry) is False

    def test_missing_numeric_field_rejected(self):
        telemetry = {
            "equipment_id": "EQ-1",
            "temperature": 95.2,
            "installation_age_hours": 1200,
            "timestamp": "2025-01-01T12:00:00Z",
        }
        assert validate_telemetry_data(telemetry) is False


class TestProcessRawTelemetry:
    """Ensure raw telemetry is validated before alert creation."""

    @patch("etl.telemetry.predict_risk", return_value={"risk_score": 0.1})
    def test_low_risk_telemetry_returns_none(self, mock_score):
        telemetry = {
            "equipment_id": "EQ-1",
            "temperature": 70.0,
            "vibration": 1.0,
            "installation_age_hours": 1000,
            "timestamp": "2025-01-01T12:00:00Z",
        }
        assert process_raw_telemetry(telemetry) is None

    def test_generated_telemetry_contains_model_features(self):
        from etl.telemetry import generate_telemetry
        from ml.scoring import FEATURES

        telemetry = generate_telemetry()

        assert set(FEATURES).issubset(telemetry)
        assert telemetry["asset_type"] in {"PUMP", "LOADING_ARM", "VALVE"}

    @patch(
        "etl.telemetry.predict_risk",
        return_value={
            "risk_score": 0.95,
            "risk_level": "CRITICAL",
            "model_version": "test-model",
            "top_features": ["vibration_mm_s"],
            "prediction_id": "prediction-1",
        },
    )
    def test_high_risk_telemetry_generates_alert(self, mock_score):
        telemetry = {
            "equipment_id": "EQ-1",
            "temperature": 110.0,
            "vibration": 7.0,
            "installation_age_hours": 15000,
            "timestamp": "2025-01-01T12:00:00Z",
        }
        alert = process_raw_telemetry(telemetry)

        assert alert is not None
        assert alert["equipment_id"] == telemetry["equipment_id"]
        assert alert["telemetry"] == telemetry
        assert alert["risk_probability"] is not None
        assert alert["task_id"] is not None
        assert alert["triggered_by_model"] is True
        assert alert["failure_code"].startswith("ERR_")

    def test_invalid_telemetry_returns_none(self):
        telemetry = {
            "equipment_id": "EQ-1",
            "temperature": 110.0,
            "vibration": "bad",
            "installation_age_hours": 15000,
            "timestamp": "2025-01-01T12:00:00Z",
        }
        assert process_raw_telemetry(telemetry) is None


class TestMLScoringIntegration:
    """End-to-end scoring against the real trained model — nothing mocked.

    These exist because every other ML test mocks ``predict_risk``/
    ``score_telemetry`` directly, which let a real schema mismatch between
    the public telemetry contract and the model's feature contract ship
    unnoticed (equipment_type vs. asset_type, missing 58 engineered
    features, an operating_state value the model was never trained on).
    Redis is optional here: with no broker reachable, feature engineering
    degrades to single-sample statistics instead of failing.
    """

    def test_legacy_telemetry_scores_without_error(self):
        """The public /alerts/telemetry contract (5 legacy fields only)
        must still produce a real prediction, not a silent failure."""
        import asyncio

        from api.ml import RiskRequest, predict_risk as predict_risk_endpoint
        from etl.telemetry import enrich_for_scoring

        legacy_payload = {
            "equipment_id": "PUMP-101",
            "temperature": 108.0,
            "vibration": 6.4,
            "installation_age_hours": 14500,
            "timestamp": "2026-09-13T00:00:00Z",
        }
        enriched = enrich_for_scoring(legacy_payload)
        result = asyncio.run(predict_risk_endpoint(RiskRequest(**enriched)))

        assert 0.0 <= result["risk_score"] <= 1.0
        assert result["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert result["equipment_type"] in {"PUMP", "LOADING_ARM", "VALVE"}

    def test_generated_telemetry_scores_without_error(self):
        """The internal Celery Beat demo generator must also score cleanly."""
        import asyncio

        from api.ml import RiskRequest, predict_risk as predict_risk_endpoint
        from etl.telemetry import generate_telemetry

        result = asyncio.run(predict_risk_endpoint(RiskRequest(**generate_telemetry())))

        assert 0.0 <= result["risk_score"] <= 1.0

    def test_repeated_readings_for_the_same_equipment_build_real_history(self):
        """Rolling features must reflect actual prior readings for a given
        equipment_id, not a self-referential copy of the current sample.

        Requires a reachable Redis (the feature-history store); skips
        cleanly otherwise since feature_engineering intentionally degrades
        to single-sample stats rather than failing when Redis is down.
        """
        import redis as redis_lib

        from config import CELERY_BROKER_URL
        from etl.telemetry import enrich_for_scoring

        try:
            redis_lib.Redis.from_url(
                CELERY_BROKER_URL, socket_connect_timeout=1, socket_timeout=1
            ).ping()
        except redis_lib.RedisError as exc:
            pytest.skip(f"No reachable Redis for feature-history test: {exc}")

        base = {
            "equipment_id": "PUMP-999",
            "temperature": 70.0,
            "installation_age_hours": 5000,
            "timestamp": "2026-09-13T00:00:00Z",
        }
        last = None
        for vibration in (1.0, 2.0, 3.0, 4.0, 5.0):
            last = enrich_for_scoring({**base, "vibration": vibration})

        # lag_1 must be the immediately preceding reading (4.0), not the
        # current one — this only holds if real history was consulted.
        assert last["vibration_mm_s_lag_1"] == 4.0
        assert last["vibration_mm_s_delta_1"] == pytest.approx(1.0)

    def test_anomalous_generated_telemetry_reliably_clears_alert_threshold(self, monkeypatch):
        """generate_telemetry()'s anomalous branch (~3 of every 7 calls —
        see etl.telemetry._ANOMALOUS_TELEMETRY_RATE/_ANOMALOUS_RANGES) must
        reliably score above ALERT_CREATION_THRESHOLD against the real
        trained model — this is what makes the demo alert/work-order/
        decision-engine path actually fire and be testable end to end,
        instead of depending on rare chance draws. Ranges were calibrated
        this way (fresh per-asset history) via direct Monte Carlo probing
        of ml.scoring: 300/300 samples cleared threshold, minimum 0.68.
        """
        import asyncio

        import redis as redis_lib

        from api.ml import RiskRequest, predict_risk as predict_risk_endpoint
        from config import CELERY_BROKER_URL
        from etl.feature_engineering import _history_key
        from etl.telemetry import ALERT_CREATION_THRESHOLD, enrich_for_scoring, generate_telemetry

        # Force the anomalous branch every call — its own probability gate
        # is tested separately; this test only needs the *ranges* to hold.
        monkeypatch.setattr("etl.telemetry.random.random", lambda: 0.0)

        try:
            client = redis_lib.Redis.from_url(
                CELERY_BROKER_URL, socket_connect_timeout=1, socket_timeout=1
            )
            client.ping()
        except redis_lib.RedisError:
            client = None

        for _ in range(10):
            telemetry = generate_telemetry()
            if client is not None:
                # Match the fresh-history conditions these ranges were
                # calibrated against, then recompute the same sensor
                # reading's rolling features against that clean history —
                # this reuses generate_telemetry()'s own random draw
                # rather than sampling a new (uncleared) asset.
                client.delete(_history_key(telemetry["asset_id"]))
                telemetry = enrich_for_scoring(telemetry)
            result = asyncio.run(predict_risk_endpoint(RiskRequest(**telemetry)))
            assert result["risk_score"] > ALERT_CREATION_THRESHOLD, (
                f"anomalous reading for {telemetry['asset_id']} scored "
                f"{result['risk_score']}, expected > {ALERT_CREATION_THRESHOLD}"
            )


# =========================================================================
# Tests: transform.py
# =========================================================================

class TestBuildWorkOrderPayload:
    """Verify the work-order payload assembly."""

    def test_basic_payload(self):
        """Test test basic payload."""
        alert = {"equipment_id": "EQ-1", "part_number": "P-100"}
        technician = {"id": "TECH-001"}
        result = build_work_order_payload(alert, technician)

        assert result["equipment_id"] == "EQ-1"
        assert result["technician_id"] == "TECH-001"
        assert result["part_number"] == "P-100"
        assert "status" not in result

    def test_does_not_mutate_inputs(self):
        """Test test does not mutate inputs."""
        alert = {"equipment_id": "EQ-1", "part_number": "P-100"}
        technician = {"id": "TECH-001"}
        result = build_work_order_payload(alert, technician)

        # Result should be a new dict, not a reference
        assert result is not alert
        assert result is not technician

    def test_includes_alert_task_id(self):
        """Ensure the alert task ID is preserved in the work-order payload."""
        alert = {
            "equipment_id": "EQ-1",
            "part_number": "P-100",
            "task_id": "ALERT-123",
        }
        technician = {"id": "TECH-001"}
        result = build_work_order_payload(alert, technician)

        assert result["alert_task_id"] == "ALERT-123"


# =========================================================================
# Tests: extract.py
# =========================================================================

class TestCheckStock:
    """Cover API success, failure, and edge cases."""

    @patch("etl.extract.requests.get")
    def test_part_in_stock(self, mock_get):
        """Test test part in stock."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "part_number": "Pump Seal Kit #A4",
            "in_stock": True,
            "quantity_available": 15,
        }
        result = check_stock("Pump Seal Kit #A4")
        assert result is not None
        assert result["in_stock"] is True
        assert result["quantity_available"] == 15

    @patch("etl.extract.requests.get")
    def test_part_out_of_stock(self, mock_get):
        """Test test part out of stock."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "part_number": "Gasket Set #B2",
            "in_stock": False,
            "quantity_available": 0,
        }
        result = check_stock("Gasket Set #B2")
        assert result is not None
        assert result["in_stock"] is False

    @patch("etl.extract.requests.get")
    def test_sends_internal_service_header(self, mock_get):
        """/api/v1/warehouse/stock requires require_internal_or_roles (see
        api/equipment.py) — an unattended ETL caller with no user session
        that omits this header always gets a 401 and the whole alert ->
        work-order pipeline silently holds before ever reaching a
        technician lookup or work-order creation."""
        from config import INTERNAL_SERVICE_TOKEN

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"in_stock": True, "quantity_available": 1}
        check_stock("Pump Seal Kit #A4")
        assert mock_get.call_args.kwargs["headers"]["X-Internal-Service"] == INTERNAL_SERVICE_TOKEN

    @patch("etl.extract.requests.get")
    def test_api_error_returns_none(self, mock_get):
        """Test test api error returns none."""
        mock_get.return_value.status_code = 500
        result = check_stock("Pump Seal Kit #A4")
        assert result is None


class TestGetTechnician:
    """Cover technician availability and API failures."""

    @patch("etl.extract.requests.get")
    def test_technician_available(self, mock_get):
        """Test test technician available."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "available_technicians": [
                {"id": "TECH-101", "name": "Alice W.", "certs": ["PUMP_SEAL"]}
            ]
        }
        result = get_technician("PUMP_SEAL")
        assert result is not None
        assert result["id"] == "TECH-101"

    @patch("etl.extract.requests.get")
    def test_sends_internal_service_header(self, mock_get):
        """/api/v1/hr/technicians/available requires require_internal_or_roles
        (see api/technicians.py) — same reasoning as
        TestCheckStock.test_sends_internal_service_header above."""
        from config import INTERNAL_SERVICE_TOKEN

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"available_technicians": []}
        get_technician("PUMP_SEAL")
        assert mock_get.call_args.kwargs["headers"]["X-Internal-Service"] == INTERNAL_SERVICE_TOKEN

    @patch("etl.extract.requests.get")
    def test_no_technician_returns_none(self, mock_get):
        """Test test no technician returns none."""
        mock_get.return_value.status_code = 404
        result = get_technician("PUMP_SEAL")
        assert result is None

    @patch("etl.extract.requests.get")
    def test_empty_list_returns_none(self, mock_get):
        """Test test empty list returns none."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"available_technicians": []}
        result = get_technician("PUMP_SEAL")
        assert result is None

    @patch("etl.extract.requests.get")
    def test_api_error_returns_none(self, mock_get):
        """Test test api error returns none."""
        mock_get.return_value.status_code = 500
        result = get_technician("PUMP_SEAL")
        assert result is None


class TestResolveCertForFailure:
    """Ensure failure codes map to correct certifications."""

    def test_seal_leak(self):
        """Test test seal leak."""
        assert resolve_cert_for_failure("ERR_SEAL_LEAK") == "PUMP_SEAL"

    def test_bearing_wear(self):
        """Test test bearing wear."""
        assert resolve_cert_for_failure("ERR_BEARING_WEAR") == "ROTATING_EQUIPMENT"

    def test_overheat(self):
        """Test test overheat."""
        assert resolve_cert_for_failure("ERR_OVERHEAT") == "HVAC"

    def test_electrical(self):
        """Test test electrical."""
        assert resolve_cert_for_failure("ERR_ELECTRICAL") == "HIGH_VOLTAGE"

    def test_unknown_code_defaults(self):
        """Test test unknown code defaults."""
        assert resolve_cert_for_failure("ERR_UNKNOWN") == "GENERAL_MAINTENANCE"

    def test_empty_code_defaults(self):
        """Test test empty code defaults."""
        assert resolve_cert_for_failure("") == "GENERAL_MAINTENANCE"


# =========================================================================
# Tests: load.py
# =========================================================================

class TestDispatchWorkOrder:
    """Cover work-order API interaction (mocked)."""

    @patch("etl.load.requests.post")
    def test_successful_dispatch(self, mock_post):
        """Test test successful dispatch."""
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            "work_order_id": "WO-ABC123",
            "status": "DISPATCHED",
        }
        payload = {
            "equipment_id": "EQ-1",
            "technician_id": "TECH-001",
            "part_number": "P-100",
        }
        result = dispatch_work_order(payload)
        assert result is not None
        assert result["work_order_id"] == "WO-ABC123"

    @patch("etl.load.requests.post")
    def test_api_rejection_returns_none(self, mock_post):
        """Test test api rejection returns none."""
        mock_post.return_value.status_code = 400
        mock_post.return_value.text = "Bad request"
        result = dispatch_work_order({})
        assert result is None

    @patch("etl.load.requests.post")
    def test_server_error_returns_none(self, mock_post):
        """Test test server error returns none."""
        mock_post.return_value.status_code = 500
        result = dispatch_work_order({})
        assert result is None


# =========================================================================
# Tests: pipeline.py (integration orchestration, mocked dependencies)
# =========================================================================

class TestProcessAlertPipeline:
    """End-to-end pipeline orchestration with all dependencies mocked."""

    @patch("etl.pipeline.dispatch_work_order")
    @patch("etl.pipeline.get_technician")
    @patch("etl.pipeline.check_stock")
    def test_full_success_path(self, mock_stock, mock_tech, mock_dispatch):
        """Test test full success path."""
        mock_stock.return_value = {"in_stock": True, "quantity_available": 10}
        mock_tech.return_value = {"id": "TECH-001", "name": "Alice W."}
        mock_dispatch.return_value = {
            "work_order_id": "WO-ABC123",
            "status": "DISPATCHED",
        }

        alert = {
            "equipment_id": "PUMP-901",
            "part_number": "Pump Seal Kit #A4",
            "severity": "HIGH",
            "failure_code": "ERR_SEAL_LEAK",
        }
        result = process_alert_pipeline(alert)
        assert result is not None
        assert result["work_order_id"] == "WO-ABC123"

    @patch("etl.pipeline.check_stock")
    def test_out_of_stock_returns_none(self, mock_stock):
        """Test test out of stock returns none."""
        mock_stock.return_value = {"in_stock": False, "quantity_available": 0}
        alert = {
            "equipment_id": "PUMP-901",
            "part_number": "Gasket Set #B2",
            "severity": "HIGH",
            "failure_code": "ERR_SEAL_LEAK",
        }
        result = process_alert_pipeline(alert)
        assert result is None

    @patch("etl.pipeline.check_stock")
    @patch("etl.pipeline.get_technician")
    def test_no_technician_returns_external_source_status(self, mock_tech, mock_stock):
        """Test test no technician returns external source hold status."""
        mock_stock.return_value = {"in_stock": True, "quantity_available": 10}
        mock_tech.return_value = None
        alert = {
            "equipment_id": "PUMP-901",
            "part_number": "Pump Seal Kit #A4",
            "severity": "HIGH",
            "failure_code": "ERR_SEAL_LEAK",
        }
        result = process_alert_pipeline(alert)
        assert result is not None
        assert result["status"] == "external_source"
        assert "No certified technician on shift" in result["reason"]

    def test_invalid_alert_returns_none(self):
        """Test test invalid alert returns none."""
        alert = {"equipment_id": ""}  # missing required keys
        result = process_alert_pipeline(alert)
        assert result is None
