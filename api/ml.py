"""Internal risk-scoring endpoint backed by the trained model artifact."""

import csv
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from api.auth import require_internal_service
from ml.explainability import explain_prediction
from ml.scoring import METADATA, score_telemetry

router = APIRouter(
    prefix="/api/v1/ml",
    tags=["ML"],
    dependencies=[Depends(require_internal_service)],
)

FEATURE_IMPORTANCE_FILE = Path(__file__).resolve().parents[1] / "ml" / "models" / "feature_importance.csv"


class RiskRequest(BaseModel):
    """Model-compatible live telemetry and equipment metadata.

    ``equipment_type`` is optional and, when omitted, is derived from the
    scoring payload's ``asset_type`` — the two are the same domain
    (PUMP/LOADING_ARM/VALVE) under different names from different callers,
    and requiring both was rejecting every caller that only knew one of them.
    """

    model_config = ConfigDict(extra="allow")
    equipment_id: str
    equipment_type: str | None = Field(default=None, pattern="^(PUMP|LOADING_ARM|VALVE)$")


class FailureMode(BaseModel):
    """A single possible failure mode identified by the rules engine."""
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]


class ExplainabilityPayload(BaseModel):
    """Per-prediction explainability fields added to the risk response."""
    anomaly_score: float = Field(ge=0.0, le=1.0)
    likely_failure_modes: list[FailureMode]
    recommended_inspection: list[str]
    requires_technician_review: bool


class RiskResponse(BaseModel):
    """Full response from the predict-risk endpoint."""
    equipment_id: str
    equipment_type: str
    risk_score: float
    risk_level: str
    prediction_horizon_hours: int
    top_features: list[str]
    model_version: str
    prediction_id: str
    timestamp: str
    anomaly_score: float
    likely_failure_modes: list[FailureMode]
    recommended_inspection: list[str]
    requires_technician_review: bool


def _top_features() -> list[str]:
    try:
        with FEATURE_IMPORTANCE_FILE.open(newline="", encoding="utf-8") as file:
            rows = csv.DictReader(file)
            return [row["feature"] for row in rows if row.get("feature")][:5]
    except (OSError, KeyError):
        return []


def _validate_categorical(telemetry: dict[str, Any], field: str) -> None:
    """Reject an unrecognised category explicitly instead of letting it
    silently become NaN inside the model (see ml.scoring.score_telemetry)."""
    value = telemetry.get(field)
    allowed = METADATA.get("categorical_values", {}).get(field)
    if value is not None and allowed is not None and value not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Unrecognised {field}: {value!r}. Expected one of {allowed}.",
        )


@router.post(
    "/predict-risk",
    response_model=RiskResponse,
    status_code=status.HTTP_200_OK,
    responses={422: {"description": "Missing equipment type or an unrecognised/incomplete feature set"}},
)
async def predict_risk(request: RiskRequest):
    telemetry: dict[str, Any] = request.model_dump(exclude_none=True)
    equipment_type = telemetry.get("equipment_type") or telemetry.get("asset_type")
    if equipment_type is None:
        raise HTTPException(
            status_code=422,
            detail="equipment_type or asset_type is required",
        )
    telemetry.setdefault("asset_type", equipment_type)
    for field in ("asset_type", "operating_state", "alarm_code"):
        _validate_categorical(telemetry, field)

    try:
        result = score_telemetry(telemetry)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    risk_score = float(result["failure_probability"])
    risk_level = "CRITICAL" if risk_score >= 0.85 else result["risk_level"]

    explanation = explain_prediction(telemetry, equipment_type, risk_score)

    return RiskResponse(
        equipment_id=request.equipment_id,
        equipment_type=equipment_type,
        risk_score=risk_score,
        risk_level=risk_level,
        prediction_horizon_hours=result.get("prediction_horizon_hours", 6),
        top_features=_top_features(),
        model_version=f"xgboost-{METADATA.get('xgboost_version', 'unknown')}",
        prediction_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        anomaly_score=explanation["anomaly_score"],
        likely_failure_modes=explanation["likely_failure_modes"],
        recommended_inspection=explanation["recommended_inspection"],
        requires_technician_review=explanation["requires_technician_review"],
    )