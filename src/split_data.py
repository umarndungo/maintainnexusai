import pandas as pd
from pathlib import Path


INPUT = Path(
    "data/processed/ml_features/telemetry_features.csv"
)

OUTPUT_DIR = Path(
    "data/processed/splits"
)

TARGET = "failure_next_6h"


TRAIN_RATIO = 0.70
VALIDATION_RATIO = 0.15
TEST_RATIO = 0.15


def create_temporal_split():

    print("Loading feature dataset...")

    df = pd.read_csv(INPUT)

    print(f"Total rows: {len(df):,}")
    print(f"Total assets: {df['asset_id'].nunique()}")

    # --------------------------------------------------
    # Validate asset row counts
    # --------------------------------------------------

    asset_counts = df["asset_id"].value_counts()

    print("\nAsset row counts:")
    print(asset_counts.to_string())

    if asset_counts.nunique() != 1:
        raise ValueError(
            "Assets do not have equal row counts. "
            "Review the dataset before splitting."
        )

    rows_per_asset = asset_counts.iloc[0]

    print(
        f"\nRows per asset: {rows_per_asset:,}"
    )

    # --------------------------------------------------
    # Calculate split boundaries
    # --------------------------------------------------

    train_size = int(
        rows_per_asset * TRAIN_RATIO
    )

    validation_size = int(
        rows_per_asset * VALIDATION_RATIO
    )

    test_size = (
        rows_per_asset
        - train_size
        - validation_size
    )

    print("\nRows per asset:")
    print(f"Train:      {train_size:,}")
    print(f"Validation: {validation_size:,}")
    print(f"Test:       {test_size:,}")

    # --------------------------------------------------
    # Create split labels within each asset
    # --------------------------------------------------

    df["_row_number"] = (
        df.groupby("asset_id")
        .cumcount()
    )

    df["_split"] = "test"

    df.loc[
        df["_row_number"] < train_size,
        "_split"
    ] = "train"

    df.loc[
        (
            df["_row_number"] >= train_size
        )
        &
        (
            df["_row_number"]
            < train_size + validation_size
        ),
        "_split"
    ] = "validation"

    # --------------------------------------------------
    # Create datasets
    # --------------------------------------------------

    train = df[df["_split"] == "train"].copy()
    validation = df[df["_split"] == "validation"].copy()
    test = df[df["_split"] == "test"].copy()

    # Remove helper columns
    for dataset in [train, validation, test]:

        dataset.drop(
            columns=["_row_number", "_split"],
            inplace=True
        )

    # --------------------------------------------------
    # Create output directory
    # --------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    train_path = OUTPUT_DIR / "train.csv"
    validation_path = OUTPUT_DIR / "validation.csv"
    test_path = OUTPUT_DIR / "test.csv"

    train.to_csv(
        train_path,
        index=False
    )

    validation.to_csv(
        validation_path,
        index=False
    )

    test.to_csv(
        test_path,
        index=False
    )

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    print("\nSplit complete.")

    print(
        f"Train rows:      {len(train):,}"
    )

    print(
        f"Validation rows: {len(validation):,}"
    )

    print(
        f"Test rows:       {len(test):,}"
    )

    print("\nExpected:")
    print(
        f"{len(df):,} total rows"
    )

    print("\nTarget distribution:")

    print(
        "\nTRAIN:"
    )
    print(
        train[TARGET]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print(
        "\nVALIDATION:"
    )
    print(
        validation[TARGET]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print(
        "\nTEST:"
    )
    print(
        test[TARGET]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nFiles created:")
    print(train_path)
    print(validation_path)
    print(test_path)


if __name__ == "__main__":
    create_temporal_split()