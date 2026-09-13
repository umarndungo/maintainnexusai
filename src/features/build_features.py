import pandas as pd
from pathlib import Path


INPUT = Path(
    "data/processed/ml_targets/telemetry_failure_target.csv"
)

OUTPUT = Path(
    "data/processed/ml_features/telemetry_features.csv"
)


TARGET = "failure_next_48h"


LEAKAGE_COLUMNS = [
    "failure_flag",
    "failure_type",
    "failure_event_start",
    "next_failure_timestamp",
    "hours_to_failure",
    "provenance",
]

SENSOR_COLUMNS = [
    "pressure_bar",
    "temperature_c",
    "flow_rate_m3h",
    "motor_current_a",
    "vibration_mm_s",
    "valve_position_pct",
]


ROLLING_WINDOWS = [5, 15, 60]


def build_features():

    print("Loading dataset...")

    df = pd.read_csv(
        INPUT,
        parse_dates=["timestamp"]
    )

    print(f"Initial rows: {len(df):,}")
    print(f"Initial columns: {len(df.columns)}")

    # --------------------------------------------------
    # 1. Sort chronologically by asset
    # --------------------------------------------------

    df = (
        df.sort_values(
            ["asset_id", "timestamp"]
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------
    # 2. Create time features
    # --------------------------------------------------

    df["hour"] = df["timestamp"].dt.hour

    df["day_of_week"] = (
        df["timestamp"].dt.dayofweek
    )

    df["month"] = (
        df["timestamp"].dt.month
    )

    df["is_weekend"] = (
        df["day_of_week"] >= 5
    ).astype(int)

    # --------------------------------------------------
    # 3. Historical sensor features
    # --------------------------------------------------

    for column in SENSOR_COLUMNS:

        print(f"Engineering features for {column}...")

        # Previous reading
        df[f"{column}_lag_1"] = (
            df.groupby("asset_id")[column]
            .shift(1)
        )

        # Change from previous reading
        df[f"{column}_delta_1"] = (
            df[column]
            - df[f"{column}_lag_1"]
        )

        # Rolling historical features
        for window in ROLLING_WINDOWS:

            shifted = (
                df.groupby("asset_id")[column]
                .shift(1)
            )

            df[f"{column}_rolling_mean_{window}"] = (
                shifted
                .groupby(df["asset_id"])
                .rolling(
                    window=window,
                    min_periods=window
                )
                .mean()
                .reset_index(
                    level=0,
                    drop=True
                )
            )

            df[f"{column}_rolling_std_{window}"] = (
                shifted
                .groupby(df["asset_id"])
                .rolling(
                    window=window,
                    min_periods=window
                )
                .std()
                .reset_index(
                    level=0,
                    drop=True
                )
            )

    # --------------------------------------------------
    # 4. Remove leakage columns
    # --------------------------------------------------

    print("Removing leakage columns...")

    df = df.drop(
        columns=[
            column
            for column in LEAKAGE_COLUMNS
            if column in df.columns
        ],
        errors="ignore"
    )

    # --------------------------------------------------
    # 5. Remove raw timestamp
    # --------------------------------------------------

    df = df.drop(
        columns=["timestamp"],
        errors="ignore"
    )

    # --------------------------------------------------
    # 6. Remove rows without complete historical windows
    # --------------------------------------------------

    # The first 60 minutes of each asset cannot have
    # a complete 60-minute historical window.

    rolling_columns = [
        column
        for column in df.columns
        if "_rolling_" in column
    ]

    df = df.dropna(
        subset=rolling_columns
    ).reset_index(drop=True)

    # --------------------------------------------------
    # 7. Save
    # --------------------------------------------------

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    print("Writing feature dataset to CSV...")

    df.to_csv(
        OUTPUT,
        index=False,
        chunksize=100_000,
        float_format="%.6g"
    )

    print("Feature dataset written successfully.")

    # --------------------------------------------------
    # 8. Validation
    # --------------------------------------------------

    print("\nFeature engineering complete.")

    print(f"Final rows: {len(df):,}")
    print(f"Final columns: {len(df.columns)}")

    print("\nOutput:")
    print(OUTPUT)

    print("\nFinal columns:")
    for column in df.columns:
        print(column)


if __name__ == "__main__":
    build_features()