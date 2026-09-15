"""Telemetry ETL — the Load step, run *before* ML scoring.

Validate (etl.ge_validation.validate_telemetry_data) and Extract+Transform
(etl.telemetry.enrich_for_scoring — pulls an asset's Redis history and
computes the 48 lag/delta/rolling-window features) already existed. This
module adds the missing Load step: persisting that validated, transformed
reading as a real row *before* it's ever sent to the model, so a durable,
queryable record exists even if the scoring call subsequently fails —
and ``etl.telemetry.score_and_decide`` calls it in exactly that order.

Kept as a thin wrapper over etl/readings_client.py (an HTTP client, not a
direct DB write) to match every other etl/*.py module's shape.
"""

import logging
from typing import Any

from etl.readings_client import create_reading, update_reading_score

logger = logging.getLogger(__name__)


def load(equipment_id: str, asset_type: str, telemetry: dict[str, Any], station_id: str | None = None) -> int | None:
    """Load step: persist the (already extracted+transformed) reading.

    Returns the new row's id, or ``None`` if the write itself failed
    (network/DB error) — callers should treat that as "no ETL record for
    this reading" and continue scoring anyway rather than aborting the
    whole telemetry pipeline over a monitoring-table write failure.
    """
    reading_id = create_reading(equipment_id, asset_type, telemetry, station_id)
    if reading_id is None:
        logger.warning("ETL Load step failed for equipment_id=%s — continuing without a reading_id.", equipment_id)
    return reading_id


def update_score(reading_id: int | None, score_result: dict[str, Any], alert_created: bool) -> None:
    """Attach an ML score to an already-loaded reading. No-op if ``load()``
    didn't produce a reading_id (nothing to attach it to)."""
    if reading_id is None:
        return
    risk_probability = score_result.get("risk_score", score_result.get("failure_probability"))
    if risk_probability is None:
        return
    update_reading_score(
        reading_id,
        risk_probability=float(risk_probability),
        risk_level=score_result.get("risk_level"),
        model_version=score_result.get("model_version"),
        top_features=score_result.get("top_features"),
        alert_created=alert_created,
    )
