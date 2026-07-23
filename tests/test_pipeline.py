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
        assert result["status"] == "CREATED"

    def test_does_not_mutate_inputs(self):
        """Test test does not mutate inputs."""
        alert = {"equipment_id": "EQ-1", "part_number": "P-100"}
        technician = {"id": "TECH-001"}
        result = build_work_order_payload(alert, technician)

        # Result should be a new dict, not a reference
        assert result is not alert
        assert result is not technician


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
            "status": "CREATED",
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
    def test_no_technician_returns_none(self, mock_tech, mock_stock):
        """Test test no technician returns none."""
        mock_stock.return_value = {"in_stock": True, "quantity_available": 10}
        mock_tech.return_value = None
        alert = {
            "equipment_id": "PUMP-901",
            "part_number": "Pump Seal Kit #A4",
            "severity": "HIGH",
            "failure_code": "ERR_SEAL_LEAK",
        }
        result = process_alert_pipeline(alert)
        assert result is None

    def test_invalid_alert_returns_none(self):
        """Test test invalid alert returns none."""
        alert = {"equipment_id": ""}  # missing required keys
        result = process_alert_pipeline(alert)
        assert result is None
