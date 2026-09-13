"""HSE early-warning analytics for spill and overfill prevention."""

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi import Depends
from pydantic import BaseModel, Field
from api.auth import get_current_user, require_roles

router = APIRouter(prefix="/api/v1/hse", tags=["HSE Safety"])


class OverfillTelemetry(BaseModel):
    tank_id: str
    level_percent: float = Field(ge=0, le=100)
    flow_rate_lpm: float = Field(ge=0)
    safe_level_percent: float = Field(default=85, gt=0, le=100)
    max_flow_rate_lpm: float = Field(default=1200, gt=0)
    capacity_liters: float = Field(default=50000, gt=0)


def assess_overfill_risk(telemetry: OverfillTelemetry) -> dict:
    """Return an explainable early-warning assessment from tank telemetry."""
    remaining_percent = max(telemetry.safe_level_percent - telemetry.level_percent, 0)
    remaining_liters = telemetry.capacity_liters * remaining_percent / 100
    minutes_to_safe_limit = remaining_liters / telemetry.flow_rate_lpm if telemetry.flow_rate_lpm else None
    rate_ratio = telemetry.flow_rate_lpm / telemetry.max_flow_rate_lpm

    if telemetry.level_percent >= telemetry.safe_level_percent or rate_ratio >= 1:
        severity = "CRITICAL"
        action = "Stop loading and notify the supervisor immediately"
    elif telemetry.level_percent >= telemetry.safe_level_percent - 5 or rate_ratio >= 0.8:
        severity = "HIGH"
        action = "Reduce flow and confirm the shutdown interlock is ready"
    elif telemetry.level_percent >= telemetry.safe_level_percent - 15 or rate_ratio >= 0.6:
        severity = "MEDIUM"
        action = "Monitor the fill cycle and verify operator readiness"
    else:
        severity = "LOW"
        action = "Continue monitored loading"

    return {
        "tank_id": telemetry.tank_id,
        "level_percent": round(telemetry.level_percent, 1),
        "safe_level_percent": telemetry.safe_level_percent,
        "flow_rate_lpm": round(telemetry.flow_rate_lpm, 1),
        "max_flow_rate_lpm": telemetry.max_flow_rate_lpm,
        "minutes_to_safe_limit": round(minutes_to_safe_limit, 1) if minutes_to_safe_limit is not None else None,
        "severity": severity,
        "recommended_action": action,
        "drivers": [
            f"Tank is {telemetry.level_percent:.1f}% full against an {telemetry.safe_level_percent:.0f}% safe limit",
            f"Flow is {telemetry.flow_rate_lpm:.0f} L/min against a {telemetry.max_flow_rate_lpm:.0f} L/min limit",
        ],
        "source": "simulated tank telemetry",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/overfill-risk")
async def overfill_risk(telemetry: OverfillTelemetry, user: dict = Depends(require_roles("engineer", "supervisor"))):
    return assess_overfill_risk(telemetry)


@router.get("/overview")
async def hse_overview(user: dict = Depends(get_current_user)):
    """Demo snapshot used by the dashboard until live tank sensors are connected."""
    return assess_overfill_risk(
        OverfillTelemetry(
            tank_id="TANK-04",
            level_percent=78.4,
            flow_rate_lpm=980,
            safe_level_percent=85,
            max_flow_rate_lpm=1200,
        )
    )
