"""Rolling-window feature engineering for the ML risk model.

The trained XGBoost model (``ml/scoring.py``) needs 48 lag/delta/rolling
features derived from an asset's *recent history*, not just its current
reading. This module maintains that history — a short list of the most
recent raw sensor readings per asset, in Redis — and computes the real
lag/delta/rolling-mean/rolling-std features from it.

This deliberately reuses the Redis instance already deployed as the Celery
broker (``CELERY_BROKER_URL``) rather than adding a new service dependency.
If Redis is unreachable, feature computation degrades to single-sample
statistics (lag/delta relative to the current reading, rolling stats over
just the current value) instead of failing the whole scoring request —
predictions are then less historically informed, but the pipeline keeps
working end to end.
"""

from __future__ import annotations

import json
import logging
import statistics
from typing import Dict, List

import redis

from config import CELERY_BROKER_URL

logger = logging.getLogger(__name__)

BASE_SENSORS = (
    "pressure_bar",
    "temperature_c",
    "flow_rate_m3h",
    "motor_current_a",
    "vibration_mm_s",
    "valve_position_pct",
)
ROLLING_WINDOWS = (5, 15, 60)
_HISTORY_LIMIT = max(ROLLING_WINDOWS)
_HISTORY_TTL_SECONDS = 60 * 60 * 24
_HISTORY_KEY_PREFIX = "maintainnexus:telemetry_history:"

_client: "redis.Redis | None" = None


def _redis_client() -> "redis.Redis":
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            CELERY_BROKER_URL,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
    return _client


def _history_key(asset_id: str) -> str:
    return f"{_HISTORY_KEY_PREFIX}{asset_id}"


def _load_history(asset_id: str) -> List[Dict[str, float]]:
    """Return the asset's past readings, most recent first. Empty on any error."""
    try:
        raw_entries = _redis_client().lrange(_history_key(asset_id), 0, _HISTORY_LIMIT - 1)
        return [json.loads(entry) for entry in raw_entries]
    except (redis.RedisError, OSError, ValueError) as exc:
        logger.warning(
            "Telemetry history unavailable for %s (%s); scoring with single-sample stats.",
            asset_id,
            exc,
        )
        return []


def _save_reading(asset_id: str, sensors: Dict[str, float]) -> None:
    """Best-effort: push the new reading onto the asset's history."""
    try:
        key = _history_key(asset_id)
        client = _redis_client()
        client.lpush(key, json.dumps(sensors))
        client.ltrim(key, 0, _HISTORY_LIMIT - 1)
        client.expire(key, _HISTORY_TTL_SECONDS)
    except (redis.RedisError, OSError, TypeError) as exc:
        logger.warning("Could not persist telemetry history for %s: %s", asset_id, exc)


def engineer_features(asset_id: str, sensors: Dict[str, float]) -> Dict[str, float]:
    """Compute the 48 lag/delta/rolling-window features for one new reading.

    Reads history *before* appending the new reading, so ``lag_1``/``delta_1``
    reflect the actual previous sample rather than the reading itself.
    """
    history = _load_history(asset_id)
    features: Dict[str, float] = {}
    for sensor in BASE_SENSORS:
        current = float(sensors[sensor])
        previous = float(history[0][sensor]) if history else current
        features[f"{sensor}_lag_1"] = previous
        features[f"{sensor}_delta_1"] = round(current - previous, 4)
        for window in ROLLING_WINDOWS:
            window_values = [current] + [
                float(reading[sensor]) for reading in history[: window - 1]
            ]
            features[f"{sensor}_rolling_mean_{window}"] = round(statistics.fmean(window_values), 4)
            features[f"{sensor}_rolling_std_{window}"] = (
                round(statistics.pstdev(window_values), 4) if len(window_values) > 1 else 0.0
            )
    _save_reading(asset_id, sensors)
    return features
