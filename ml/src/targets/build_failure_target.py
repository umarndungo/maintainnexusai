import pandas as pd
import numpy as np
from pathlib import Path


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

INPUT_FILE = Path(
    "data/processed/unified/asset_telemetry.csv"
)

OUTPUT_DIR = Path(
    "data/processed/ml_targets"
)

OUTPUT_FILE = OUTPUT_DIR / "telemetry_failure_target.csv"

HORIZON_HOURS = 6


# ------------------------------------------------------------
# Load telemetry
# ------------------------------------------------------------

print("Loading telemetry...")

df = pd.read_csv(
    INPUT_FILE,
    parse_dates=["timestamp"],
)

print(f"Loaded {len(df):,} telemetry records.")


# ------------------------------------------------------------
# Sort telemetry
# ------------------------------------------------------------

df = (
    df.sort_values(
        ["asset_id", "timestamp"]
    )
    .reset_index(drop=True)
)


# ------------------------------------------------------------
# Identify failure events
# ------------------------------------------------------------
#
# A failure event starts when:
#
# current row      = failure
# previous row     = not failure
#
# This prevents a 10-minute failure event from being
# treated as 10 separate failure events.
# ------------------------------------------------------------

previous_failure = (
    df.groupby("asset_id")["failure_flag"]
    .shift(fill_value=0)
)

df["failure_event_start"] = (
    (df["failure_flag"] == 1)
    & (previous_failure == 0)
)


# ------------------------------------------------------------
# Find the next future failure event for each asset
# ------------------------------------------------------------

def assign_next_failure(group):
    """
    For every telemetry timestamp belonging to one asset,
    find the next failure event that occurs strictly after
    that timestamp.
    """

    group = group.sort_values("timestamp").copy()

    failure_events = group.loc[
        group["failure_event_start"],
        "timestamp"
    ]

    if failure_events.empty:
        group["next_failure_timestamp"] = pd.NaT
        return group

    failure_times = failure_events.to_numpy(
        dtype="datetime64[ns]"
    )

    current_times = group["timestamp"].to_numpy(
        dtype="datetime64[ns]"
    )

    # Search only for failure events strictly AFTER
    # the current telemetry timestamp.
    positions = np.searchsorted(
        failure_times,
        current_times,
        side="right",
    )

    next_failure = np.full(
        len(group),
        np.datetime64("NaT", "ns"),
        dtype="datetime64[ns]",
    )

    valid = positions < len(failure_times)

    next_failure[valid] = failure_times[
        positions[valid]
    ]

    group["next_failure_timestamp"] = next_failure

    return group.reset_index(drop=True)


groups = []

for asset_id, group in df.groupby("asset_id"):

    result = assign_next_failure(group)

    result["asset_id"] = asset_id

    groups.append(result)

df = pd.concat(
    groups,
    ignore_index=True
)

# ------------------------------------------------------------
# Calculate time until next failure
# ------------------------------------------------------------

df["hours_to_failure"] = (
    df["next_failure_timestamp"]
    - df["timestamp"]
).dt.total_seconds() / 3600


# ------------------------------------------------------------
# Create future failure target
# ------------------------------------------------------------
#
# failure_next_6h = 1 when:
#
#   1. A future failure exists
#   2. It occurs within 6 hours
#
# Otherwise:
#
#   failure_next_6h = 0
#
# Current failure rows are excluded because the target
# only looks strictly into the future.
# ------------------------------------------------------------

df["failure_next_6h"] = (
    (df["hours_to_failure"] > 0)
    & (df["hours_to_failure"] <= HORIZON_HOURS)
).astype(int)


# ------------------------------------------------------------
# Save ML target dataset
# ------------------------------------------------------------

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

df.to_csv(
    OUTPUT_FILE,
    index=False,
)


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

print()
print("=" * 60)
print("FAILURE TARGET GENERATION COMPLETE")
print("=" * 60)

print(f"Output: {OUTPUT_FILE}")
print(f"Rows: {len(df):,}")

print()
print("Failure events detected:")

failure_event_count = (
    df["failure_event_start"]
    .sum()
)

print(
    f"Total failure events: {failure_event_count}"
)

print(
    "Assets with failure events: "
    f"{df.loc[df['failure_event_start'], 'asset_id'].nunique()}"
)

print()
print("Target distribution:")

print(
    df["failure_next_6h"]
    .value_counts()
    .sort_index()
)

print()
print("Target percentages:")

print(
    df["failure_next_6h"]
    .value_counts(normalize=True)
    .sort_index()
    .mul(100)
    .round(2)
)

print()
print("Target columns created:")
print("  failure_event_start")
print("  next_failure_timestamp")
print("  hours_to_failure")
print("  failure_next_6h")