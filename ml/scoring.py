from pathlib import Path
import json
from typing import Any, Dict

import pandas as pd
import xgboost as xgb


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"

MODEL_FILE = MODEL_DIR / "maintainnexus_xgboost.json"
METADATA_FILE = MODEL_DIR / "model_metadata.json"


# ============================================================
# LOAD MODEL METADATA
# ============================================================

with open(METADATA_FILE, "r", encoding="utf-8") as file:
    METADATA = json.load(file)


MODEL = xgb.XGBClassifier()

MODEL.load_model(MODEL_FILE)


TARGET = METADATA["target"]
THRESHOLD = float(METADATA["threshold"])
FEATURES = METADATA["features"]
CATEGORICAL_FEATURES = METADATA["categorical_features"]


# ============================================================
# SCORING
# ============================================================

def score_telemetry(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score one telemetry record using the trained XGBoost model.

    Returns:
        failure_probability
        failure_predicted
        risk_level
        threshold
    """

    # --------------------------------------------------------
    # Convert payload to DataFrame
    # --------------------------------------------------------

    row = pd.DataFrame([telemetry])

    # --------------------------------------------------------
    # Validate required features
    # --------------------------------------------------------

    missing_features = [
        feature
        for feature in FEATURES
        if feature not in row.columns
    ]

    if missing_features:
        raise ValueError(
            "Missing required model features: "
            + ", ".join(missing_features)
        )

    # --------------------------------------------------------
    # Keep only trained model features
    # --------------------------------------------------------

    row = row[FEATURES].copy()

    # --------------------------------------------------------
    # Restore categorical types
    # --------------------------------------------------------

    for column in CATEGORICAL_FEATURES:

        categories = METADATA[
            "categorical_values"
        ][column]

        row[column] = pd.Categorical(
            row[column].astype("string"),
            categories=categories,
        )

    # --------------------------------------------------------
    # Generate probability
    # --------------------------------------------------------

    probability = float(
        MODEL.predict_proba(row)[0][1]
    )

    # --------------------------------------------------------
    # Apply saved validation threshold
    # --------------------------------------------------------

    failure_predicted = (
        probability >= THRESHOLD
    )

    # --------------------------------------------------------
    # Risk classification
    # --------------------------------------------------------

    if probability >= 0.50:
        risk_level = "HIGH"

    elif probability >= THRESHOLD:
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    # --------------------------------------------------------
    # Return prediction
    # --------------------------------------------------------

    return {
        "failure_probability": round(
            probability,
            4,
        ),
        "failure_predicted": bool(
            failure_predicted
        ),
        "risk_level": risk_level,
        "threshold": round(
            THRESHOLD,
            4,
        ),
        "prediction_horizon_hours": 6,
        "target": TARGET,
    }