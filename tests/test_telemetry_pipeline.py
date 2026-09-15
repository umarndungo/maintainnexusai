"""Tests for the telemetry ETL Load step running *before* ML scoring
(etl/telemetry_pipeline.py, wired into etl.telemetry.score_and_decide).
"""

from unittest.mock import patch

from etl.telemetry import score_and_decide


def test_load_runs_before_ml_and_update_score_runs_after():
    calls: list[str] = []

    def fake_load(equipment_id, asset_type, telemetry, station_id=None):
        calls.append("load")
        assert equipment_id == "PUMP-1"
        return 42

    def fake_predict_risk(enriched):
        calls.append("ml")
        return {"risk_score": 0.05, "risk_level": "LOW", "model_version": "test-model"}

    def fake_update_score(reading_id, score_result, alert_created):
        calls.append("update_score")
        assert reading_id == 42
        assert alert_created is False

    telemetry = {
        "equipment_id": "PUMP-1",
        "temperature": 70.0,
        "vibration": 1.0,
        "installation_age_hours": 1000,
        "timestamp": "2025-01-01T12:00:00Z",
    }

    with patch("etl.telemetry_pipeline.load", side_effect=fake_load) as load_mock, \
         patch("etl.telemetry.predict_risk", side_effect=fake_predict_risk), \
         patch("etl.telemetry_pipeline.update_score", side_effect=fake_update_score) as update_mock:
        score_result, alert = score_and_decide(telemetry)

    # Order matters: the ETL row must exist before ML is ever called.
    assert calls == ["load", "ml", "update_score"]
    assert score_result == {"risk_score": 0.05, "risk_level": "LOW", "model_version": "test-model"}
    assert alert is None
    load_mock.assert_called_once()
    update_mock.assert_called_once()


def test_validation_failure_never_calls_load():
    telemetry = {"equipment_id": "PUMP-1"}  # missing required fields

    with patch("etl.telemetry_pipeline.load") as load_mock:
        score_result, alert = score_and_decide(telemetry)

    assert score_result is None
    assert alert is None
    load_mock.assert_not_called()


def test_load_failure_does_not_block_scoring():
    """If the Load step's HTTP call fails, score_and_decide must still
    proceed to ML rather than aborting — a monitoring-table write
    failure shouldn't take down alerting."""
    telemetry = {
        "equipment_id": "PUMP-1",
        "temperature": 110.0,
        "vibration": 7.0,
        "installation_age_hours": 15000,
        "timestamp": "2025-01-01T12:00:00Z",
    }

    with patch("etl.telemetry_pipeline.load", return_value=None), \
         patch("etl.telemetry.predict_risk", return_value={"risk_score": 0.95, "risk_level": "CRITICAL"}), \
         patch("etl.telemetry_pipeline.update_score") as update_mock:
        score_result, alert = score_and_decide(telemetry)

    assert score_result["risk_score"] == 0.95
    assert alert is not None  # still builds the alert
    update_mock.assert_called_once_with(None, {"risk_score": 0.95, "risk_level": "CRITICAL"}, True)


def test_update_score_is_a_noop_without_a_reading_id():
    from etl import telemetry_pipeline

    with patch("etl.readings_client.update_reading_score") as update_mock:
        telemetry_pipeline.update_score(None, {"risk_score": 0.9}, True)

    update_mock.assert_not_called()
