import logging
from pathlib import Path
import json
from typing import Any, Dict

import numpy as np
import pandas as pd
import shap
import xgboost as xgb

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"

MODEL_FILE = MODEL_DIR / "maintainnexus_xgboost.json"
METADATA_FILE = MODEL_DIR / "model_metadata.json"


with open(METADATA_FILE, "r", encoding="utf-8") as file:
    METADATA = json.load(file)


MODEL = xgb.XGBClassifier()
MODEL.load_model(MODEL_FILE)

TARGET = METADATA["target"]
THRESHOLD = float(METADATA["threshold"])
FEATURES = METADATA["features"]
CATEGORICAL_FEATURES = METADATA["categorical_features"]


def _build_explainer() -> "shap.TreeExplainer | None":
    """Best-effort SHAP explainer construction.

    This model's saved base_score is a bracketed-string ("[3.576514E-2]")
    -- the format whichever xgboost trained/saved model.json used -- and
    shap's TreeExplainer parses that field itself (XGBTreeModelLoader,
    bypassing xgboost's own loader), not the numeric-string format shap
    releases installable on this deployment's Python 3.10 base image
    understand (shap>=0.50.0, which does handle it, requires Python
    >=3.11). Downgrading xgboost doesn't help either -- the file's
    on-disk format was fixed at save time regardless of which xgboost
    version loads it for inference now.

    Explanations are an added-value feature, not something the alert /
    decision-engine / work-order pipeline depends on, so a failure here
    must not take the whole API down (as it did before this guard existed
    -- api/ml.py imports this module at startup). score_telemetry() below
    degrades to an empty explanation rather than crashing.
    """
    try:
        return shap.TreeExplainer(MODEL)
    except Exception:  # noqa: BLE001 - genuinely any construction failure should degrade, not crash the API
        logger.warning(
            "SHAP TreeExplainer unavailable for this model/environment combination; "
            "predictions will continue without explanations.",
            exc_info=True,
        )
        return None


EXPLAINER = _build_explainer()


def _json_number(value: Any) -> float:
    """Convert NumPy/scalar values to JSON-safe Python floats."""
    value = float(value)

    if not np.isfinite(value):
        return 0.0

    return value


def _prepare_features(telemetry: Dict[str, Any]) -> pd.DataFrame:
    """Build the exact feature frame expected by the trained model."""

    missing_features = [
        feature
        for feature in FEATURES
        if feature not in telemetry
    ]

    if missing_features:
        raise ValueError(
            f"Missing required model features: {missing_features}"
        )

    row = pd.DataFrame([telemetry])

    row = row[FEATURES].copy()

    for column in CATEGORICAL_FEATURES:
        categories = METADATA["categorical_values"][column]

        row[column] = pd.Series(
            pd.Categorical(
                row[column].astype("string"),
                categories=categories,
            ),
            index=row.index,
        )

    return row


def _extract_shap_values(row: pd.DataFrame) -> np.ndarray:
    """
    Calculate Tree SHAP values for one prediction.

    For binary XGBoost classification with the default TreeExplainer
    output, this returns one SHAP value per model feature.
    """

    shap_values = EXPLAINER.shap_values(row)

    # Handle possible future/multiple-output SHAP shapes.
    if isinstance(shap_values, list):
        shap_values = shap_values[-1]

    shap_values = np.asarray(shap_values)

    if shap_values.ndim == 3:
        shap_values = shap_values[0, :, -1]
    elif shap_values.ndim == 2:
        shap_values = shap_values[0]
    elif shap_values.ndim != 1:
        raise ValueError(
            f"Unexpected SHAP output shape: {shap_values.shape}"
        )

    return shap_values


def score_telemetry(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score one telemetry observation and return the prediction,
    risk classification, and local SHAP explanation.
    """

    row = _prepare_features(telemetry)

    probability = float(
        MODEL.predict_proba(row)[0][1]
    )

    if probability >= 0.50:
        risk_level = "HIGH"
    elif probability >= THRESHOLD:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    failure_predicted = probability >= THRESHOLD

    # ---------------------------------------------------------
    # SHAP LOCAL EXPLANATION -- skipped when _build_explainer()
    # couldn't construct one (see its docstring); a prediction must
    # still come back, just without the increasing/reducing feature
    # breakdown.
    # ---------------------------------------------------------

    if EXPLAINER is None:
        return {
            "failure_probability": round(probability, 4),
            "failure_predicted": bool(failure_predicted),
            "risk_level": risk_level,
            "threshold": THRESHOLD,
            "prediction_horizon_hours": 6,
            "target": TARGET,
            "explanation": {
                "method": "unavailable",
                "output_space": None,
                "increasing_risk": [],
                "reducing_risk": [],
            },
        }

    shap_values = _extract_shap_values(row)

    contributions = pd.DataFrame(
        {
            "feature": FEATURES,
            "contribution": shap_values,
        }
    )

    contributions["contribution"] = contributions[
        "contribution"
    ].astype(float)

    increasing = (
        contributions[
            contributions["contribution"] > 0
        ]
        .sort_values(
            "contribution",
            ascending=False,
        )
        .head(5)
    )

    reducing = (
        contributions[
            contributions["contribution"] < 0
        ]
        .sort_values(
            "contribution",
            ascending=True,
        )
        .head(5)
    )

    increasing_risk = []

    for _, item in increasing.iterrows():
        feature = item["feature"]

        increasing_risk.append(
            {
                "feature": feature,
                "contribution": _json_number(
                    item["contribution"]
                ),
                "value": _json_number(
                    row.iloc[0][feature]
                )
                if pd.api.types.is_numeric_dtype(row[feature])
                else str(row.iloc[0][feature]),
            }
        )

    reducing_risk = []

    for _, item in reducing.iterrows():
        feature = item["feature"]

        reducing_risk.append(
            {
                "feature": feature,
                "contribution": _json_number(
                    item["contribution"]
                ),
                "value": _json_number(
                    row.iloc[0][feature]
                )
                if pd.api.types.is_numeric_dtype(row[feature])
                else str(row.iloc[0][feature]),
            }
        )

    return {
        "failure_probability": round(probability, 4),
        "failure_predicted": bool(failure_predicted),
        "risk_level": risk_level,
        "threshold": THRESHOLD,
        "prediction_horizon_hours": 6,
        "target": TARGET,
        "explanation": {
            "method": "SHAP TreeExplainer",
            "output_space": "raw_margin",
            "increasing_risk": increasing_risk,
            "reducing_risk": reducing_risk,
        },
    }