from pathlib import Path
import pandas as pd


# ============================================================
# MaintainNexusAI - Unified Data Layer
# ============================================================

INPUT_DIR = Path("data/processed/operational")
OUTPUT_DIR = Path("data/processed/unified")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# Dataset configuration
# ------------------------------------------------------------

FILES = [
    "asset_master.csv",
    "asset_relationships.csv",
    "asset_telemetry.csv",
    "alarm_events.csv",
    "loading_operations.csv",
    "maintenance_work_orders.csv",
]


# ------------------------------------------------------------
# Load and standardize datasets
# ------------------------------------------------------------

datasets = {}

for filename in FILES:

    input_path = INPUT_DIR / filename

    if not input_path.exists():
        raise FileNotFoundError(
            f"Validated dataset not found: {input_path}"
        )

    df = pd.read_csv(input_path)

    datasets[filename.replace(".csv", "")] = df

    print(
        f"Loaded {filename}: {len(df):,} rows"
    )


# ------------------------------------------------------------
# Standardize timestamps
# ------------------------------------------------------------

datasets["asset_telemetry"]["timestamp"] = pd.to_datetime(
    datasets["asset_telemetry"]["timestamp"],
    errors="coerce",
)

datasets["alarm_events"]["timestamp"] = pd.to_datetime(
    datasets["alarm_events"]["timestamp"],
    errors="coerce",
)

datasets["loading_operations"]["start_time"] = pd.to_datetime(
    datasets["loading_operations"]["start_time"],
    errors="coerce",
)

datasets["loading_operations"]["end_time"] = pd.to_datetime(
    datasets["loading_operations"]["end_time"],
    errors="coerce",
)

datasets["maintenance_work_orders"]["maintenance_start"] = pd.to_datetime(
    datasets["maintenance_work_orders"]["maintenance_start"],
    errors="coerce",
)

datasets["maintenance_work_orders"]["maintenance_end"] = pd.to_datetime(
    datasets["maintenance_work_orders"]["maintenance_end"],
    errors="coerce",
)


# ------------------------------------------------------------
# Save unified datasets
# ------------------------------------------------------------

print()
print("Writing unified data layer...")

for name, df in datasets.items():

    output_path = OUTPUT_DIR / f"{name}.csv"

    df.to_csv(
        output_path,
        index=False,
    )

    print(
        f"  {output_path}: {len(df):,} rows"
    )


# ------------------------------------------------------------
# Create unified asset view
#
# This connects:
# Asset Master
#       +
# Asset Relationships
#
# It gives us a useful operational view of the equipment
# and its associated pump/valve/loading-arm path.
# ------------------------------------------------------------

assets = datasets["asset_master"].copy()
relationships = datasets["asset_relationships"].copy()


# Create a loading-arm relationship view

relationship_view = relationships.merge(
    assets.add_prefix("pump_asset_"),
    left_on="pump_id",
    right_on="pump_asset_asset_id",
    how="left",
)

relationship_view = relationship_view.merge(
    assets.add_prefix("valve_asset_"),
    left_on="valve_id",
    right_on="valve_asset_asset_id",
    how="left",
)

relationship_view = relationship_view.merge(
    assets.add_prefix("arm_asset_"),
    left_on="loading_arm_id",
    right_on="arm_asset_asset_id",
    how="left",
)


relationship_output = OUTPUT_DIR / "asset_relationship_view.csv"

relationship_view.to_csv(
    relationship_output,
    index=False,
)

print(
    f"  {relationship_output}: "
    f"{len(relationship_view):,} rows"
)


# ------------------------------------------------------------
# Create telemetry + asset context view
#
# This is the first useful analytical dataset for prediction.
#
# Telemetry tells us:
#   What is the equipment doing?
#
# Asset master tells us:
#   What equipment is it?
#   Where is it?
#   How critical is it?
# ------------------------------------------------------------

telemetry = datasets["asset_telemetry"].copy()

telemetry_asset_view = telemetry.merge(
    assets,
    on="asset_id",
    how="left",
    suffixes=("", "_master"),
)


telemetry_output = OUTPUT_DIR / "telemetry_asset_view.csv"

telemetry_asset_view.to_csv(
    telemetry_output,
    index=False,
)

print(
    f"  {telemetry_output}: "
    f"{len(telemetry_asset_view):,} rows"
)


# ------------------------------------------------------------
# Final summary
# ------------------------------------------------------------

print()
print("=" * 60)
print("UNIFIED DATA LAYER COMPLETE")
print("=" * 60)

print()
print(f"Output directory: {OUTPUT_DIR}")

print()
print("Datasets available:")

for file in sorted(OUTPUT_DIR.glob("*.csv")):

    df = pd.read_csv(file)

    print(
        f"  {file.name:<35} "
        f"{len(df):>8,} rows"
    )

print()
print("Next stage:")
print("Feature engineering for failure prediction")