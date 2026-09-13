"""Internal risk-scoring endpoint backed by the trained model artifact."""

import csv
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from api.auth import require_internal_service
from ml.scoring import METADATA, score_telemetry

router = APIRouter(
    prefix="/api/v1/ml",
    tags=["ML"],
    dependencies=[Depends(require_internal_service)],
)

FEATURE_IMPORTANCE_FILE = Path(__file__).resolve().parents[1] / "ml" / "models" / "feature_importance.csv"


class RiskRequest(BaseModel):
    """Model-compatible live telemetry and equipment metadata."""

    model_config = ConfigDict(extra="allow")
    equipment_id: str
    equipment_type: str = Field(pattern="^(PUMP|LOADING_ARM|VALVE)$")


def _top_features() -> list[str]:
    try:
        with FEATURE_IMPORTANCE_FILE.open(newline="", encoding="utf-8") as file:
            rows = csv.DictReader(file)
            return [row["feature"] for row in rows if row.get("feature")][:5]
    except (OSError, KeyError):
        return []


@router.post("/predict-risk", status_code=status.HTTP_200_OK)
async def predict_risk(request: RiskRequest):
    telemetry: dict[str, Any] = request.model_dump(exclude_none=True)
    try:
        result = score_telemetry(telemetry)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    risk_score = float(result["failure_probability"])
    risk_level = "CRITICAL" if risk_score >= 0.85 else result["risk_level"]
    return {
        "equipment_id": request.equipment_id,
        "equipment_type": request.equipment_type,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "prediction_horizon_hours": result.get("prediction_horizon_hours", 6),
        "top_features": _top_features(),
        "model_version": f"xgboost-{METADATA.get('xgboost_version', 'unknown')}",
        "prediction_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }