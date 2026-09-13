from pathlib import Path
import json

import numpy as np
import pandas as pd
import xgboost as xgb

from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


# ============================================================
# PATHS
# ============================================================

DATA_DIR = Path("data/processed/splits")
MODEL_DIR = Path("ml/models")

TRAIN_FILE = DATA_DIR / "train.csv"
VALIDATION_FILE = DATA_DIR / "validation.csv"
TEST_FILE = DATA_DIR / "test.csv"

MODEL_FILE = MODEL_DIR / "maintainnexus_xgboost.json"
METADATA_FILE = MODEL_DIR / "model_metadata.json"
IMPORTANCE_FILE = MODEL_DIR / "feature_importance.csv"

TARGET = "failure_next_6h"


# ============================================================
# FEATURES
# ============================================================

CATEGORICAL_FEATURES = [
    "asset_id",
    "asset_type",
    "operating_state",
    "alarm_code",
]

# Calendar features were excluded because the first model
# relied too heavily on synthetic calendar patterns.
EXCLUDED_FEATURES = [
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
]


# ============================================================
# LOAD DATA
# ============================================================

def load_data(path):

    print(f"\nLoading {path}...")

    df = pd.read_csv(path)

    print(f"Rows:    {len(df):,}")
    print(f"Columns: {len(df.columns)}")

    return df


# ============================================================
# PREPARE CATEGORIES
# ============================================================

def prepare_categories(
    train,
    validation,
    test,
):

    print("\nPreparing categorical features...")

    for column in CATEGORICAL_FEATURES:

        categories = pd.Index(
            train[column]
            .astype("string")
            .dropna()
            .unique()
        )

        train[column] = pd.Categorical(
            train[column].astype("string"),
            categories=categories,
        )

        validation[column] = pd.Categorical(
            validation[column].astype("string"),
            categories=categories,
        )

        test[column] = pd.Categorical(
            test[column].astype("string"),
            categories=categories,
        )

        print(
            f"{column}: {len(categories)} categories"
        )

    return train, validation, test


# ============================================================
# EVALUATION
# ============================================================

def evaluate(
    name,
    y_true,
    probabilities,
    threshold,
):

    predictions = (
        probabilities >= threshold
    ).astype(int)

    precision = precision_score(
        y_true,
        predictions,
        zero_division=0,
    )

    recall = recall_score(
        y_true,
        predictions,
        zero_division=0,
    )

    f1 = f1_score(
        y_true,
        predictions,
        zero_division=0,
    )

    roc_auc = roc_auc_score(
        y_true,
        probabilities,
    )

    pr_auc = average_precision_score(
        y_true,
        probabilities,
    )

    print("\n" + "=" * 65)
    print(name)
    print("=" * 65)

    print(f"Threshold: {threshold:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1:        {f1:.4f}")
    print(f"ROC-AUC:   {roc_auc:.4f}")
    print(f"PR-AUC:    {pr_auc:.4f}")

    print("\nConfusion matrix:")
    print(
        confusion_matrix(
            y_true,
            predictions,
        )
    )

    print("\nClassification report:")
    print(
        classification_report(
            y_true,
            predictions,
            zero_division=0,
        )
    )

    return {
        "threshold": float(threshold),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
    }


# ============================================================
# THRESHOLD SELECTION
# ============================================================

def find_best_threshold(
    y_true,
    probabilities,
):

    print("\nSearching validation thresholds...")

    thresholds = np.arange(
        0.05,
        0.96,
        0.01,
    )

    best_threshold = 0.50
    best_f1 = -1.0

    for threshold in thresholds:

        predictions = (
            probabilities >= threshold
        ).astype(int)

        score = f1_score(
            y_true,
            predictions,
            zero_division=0,
        )

        if score > best_f1:

            best_f1 = score
            best_threshold = threshold

    print(
        f"Best validation threshold: "
        f"{best_threshold:.2f}"
    )

    print(
        f"Best validation F1: "
        f"{best_f1:.4f}"
    )

    return float(best_threshold)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 65)
    print("MAINTAINNEXUSAI — XGBOOST MODEL TRAINING")
    print("=" * 65)

    # --------------------------------------------------------
    # Load datasets
    # --------------------------------------------------------

    train = load_data(TRAIN_FILE)
    validation = load_data(VALIDATION_FILE)
    test = load_data(TEST_FILE)

    # --------------------------------------------------------
    # Separate target
    # --------------------------------------------------------

    X_train = train.drop(
        columns=[TARGET] + EXCLUDED_FEATURES
    )

    y_train = train[TARGET]

    X_validation = validation.drop(
        columns=[TARGET] + EXCLUDED_FEATURES
    )

    y_validation = validation[TARGET]

    X_test = test.drop(
        columns=[TARGET] + EXCLUDED_FEATURES
    )

    y_test = test[TARGET]

    # --------------------------------------------------------
    # Prepare categorical variables
    # --------------------------------------------------------

    (
        X_train,
        X_validation,
        X_test,
    ) = prepare_categories(
        X_train,
        X_validation,
        X_test,
    )

    # --------------------------------------------------------
    # Feature list
    # --------------------------------------------------------

    feature_names = list(
        X_train.columns
    )

    print(
        f"\nTotal model features: "
        f"{len(feature_names)}"
    )

    print("\nExcluded features:")

    for column in EXCLUDED_FEATURES:
        print(f"  {column}")

    # --------------------------------------------------------
    # Target summary
    # --------------------------------------------------------

    print("\nTarget distribution:")

    print("\nTRAIN:")
    print(
        y_train.value_counts()
        .sort_index()
    )

    print("\nVALIDATION:")
    print(
        y_validation.value_counts()
        .sort_index()
    )

    print("\nTEST:")
    print(
        y_test.value_counts()
        .sort_index()
    )

    # --------------------------------------------------------
    # Build XGBoost model
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print("BUILDING XGBOOST MODEL")
    print("=" * 65)

    model = xgb.XGBClassifier(
        objective="binary:logistic",
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        min_child_weight=5,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        tree_method="hist",
        eval_metric="aucpr",
        enable_categorical=True,
        random_state=42,
        n_jobs=-1,
        early_stopping_rounds=30,
    )

    # --------------------------------------------------------
    # Train
    # --------------------------------------------------------

    print("\nStarting XGBoost training...")
    print(
        "Early stopping monitors validation PR-AUC."
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[
            (
                X_validation,
                y_validation,
            )
        ],
        verbose=25,
    )

    print("\nTraining complete.")

    print(
        f"Best iteration: "
        f"{model.best_iteration}"
    )

    # --------------------------------------------------------
    # Validation predictions
    # --------------------------------------------------------

    print(
        "\nGenerating validation probabilities..."
    )

    validation_probabilities = (
        model.predict_proba(
            X_validation
        )[:, 1]
    )

    evaluate(
        "VALIDATION — threshold 0.50",
        y_validation,
        validation_probabilities,
        0.50,
    )

    # --------------------------------------------------------
    # Select threshold using validation only
    # --------------------------------------------------------

    best_threshold = find_best_threshold(
        y_validation,
        validation_probabilities,
    )

    validation_metrics = evaluate(
        "VALIDATION — selected threshold",
        y_validation,
        validation_probabilities,
        best_threshold,
    )

    # --------------------------------------------------------
    # Test evaluation
    # --------------------------------------------------------

    print(
        "\nGenerating test probabilities..."
    )

    test_probabilities = (
        model.predict_proba(
            X_test
        )[:, 1]
    )

    test_metrics = evaluate(
        "TEST — selected validation threshold",
        y_test,
        test_probabilities,
        best_threshold,
    )

    # --------------------------------------------------------
    # Save model
    # --------------------------------------------------------

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("\nSaving XGBoost model...")

    model.save_model(
        MODEL_FILE
    )

    # --------------------------------------------------------
    # Save metadata
    # --------------------------------------------------------

    category_metadata = {}

    for column in CATEGORICAL_FEATURES:

        category_metadata[column] = [
            str(value)
            for value in X_train[column].cat.categories
        ]

    metadata = {
        "model_type": "XGBoost",
        "xgboost_version": xgb.__version__,
        "target": TARGET,
        "threshold": best_threshold,
        "features": feature_names,
        "categorical_features": CATEGORICAL_FEATURES,
        "excluded_features": EXCLUDED_FEATURES,
        "categorical_values": category_metadata,
        "best_iteration": int(
            model.best_iteration
        ),
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
    }

    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            indent=4,
        )

    # --------------------------------------------------------
    # Feature importance
    # --------------------------------------------------------

    importance = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": model.feature_importances_,
        }
    ).sort_values(
        "importance",
        ascending=False,
    )

    importance.to_csv(
        IMPORTANCE_FILE,
        index=False,
    )

    # --------------------------------------------------------
    # Final output
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print("MODEL ARTIFACTS SAVED")
    print("=" * 65)

    print(f"Model:       {MODEL_FILE}")
    print(f"Metadata:    {METADATA_FILE}")
    print(f"Importance:  {IMPORTANCE_FILE}")

    print("\nTop 15 features:")

    print(
        importance.head(15).to_string(
            index=False
        )
    )

    print("\nMODEL TRAINING COMPLETE.")


if __name__ == "__main__":
    main()