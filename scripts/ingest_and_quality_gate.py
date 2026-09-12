import json
from pathlib import Path

import pandas as pd


# ============================================================
# MaintainNexusAI - Data Ingestion & Quality Gate
# ============================================================

RAW_DIR = Path("data/raw/synthetic_kpc")
PROCESSED_DIR = Path("data/processed/operational")
QUALITY_DIR = Path("data/processed/quality")

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
QUALITY_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# Required files and columns
# ------------------------------------------------------------

REQUIRED_COLUMNS = {
    "asset_master.csv": [
        "asset_id",
        "asset_type",
        "station_id",
        "location",
        "criticality",
        "status",
        "provenance",
    ],
    "asset_relationships.csv": [
        "pump_id",
        "valve_id",
        "loading_arm_id",
        "station_id",
        "relationship_type",
        "provenance",
    ],
    "asset_telemetry.csv": [
        "timestamp",
        "asset_id",
        "asset_type",
        "pressure_bar",
        "temperature_c",
        "flow_rate_m3h",
        "motor_current_a",
        "vibration_mm_s",
        "valve_position_pct",
        "operating_state",
        "alarm_code",
        "failure_flag",
        "failure_type",
        "provenance",
    ],
    "loading_operations.csv": [
        "loading_operation_id",
        "start_time",
        "end_time",
        "truck_id",
        "loading_arm_id",
        "assigned_pump",
        "assigned_valve",
        "product",
        "volume_litres",
        "operation_status",
        "provenance",
    ],
    "maintenance_work_orders.csv": [
        "work_order_id",
        "asset_id",
        "maintenance_start",
        "maintenance_end",
        "failure_type",
        "maintenance_type",
        "maintenance_action",
        "technician",
        "resolution",
        "provenance",
    ],
    "alarm_events.csv": [
        "alarm_id",
        "timestamp",
        "asset_id",
        "alarm_code",
        "severity",
        "status",
        "provenance",
    ],
}


# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

datasets = {}

for filename in REQUIRED_COLUMNS:

    path = RAW_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError(f"{filename} is empty")

    datasets[filename] = df


# ------------------------------------------------------------
# Quality report structure
# ------------------------------------------------------------

report = {
    "datasets": {},
    "overall_status": "PASS",
}


def record_result(dataset, check, passed, details=""):

    if dataset not in report["datasets"]:
        report["datasets"][dataset] = {}

    report["datasets"][dataset][check] = {
        "status": "PASS" if passed else "FAIL",
        "details": details,
    }

    if not passed:
        report["overall_status"] = "FAIL"


def check_dataset(filename, df):

    # Schema
    missing_columns = [
        column
        for column in REQUIRED_COLUMNS[filename]
        if column not in df.columns
    ]

    record_result(
        filename,
        "schema",
        len(missing_columns) == 0,
        f"Missing columns: {missing_columns}"
        if missing_columns
        else "All required columns present",
    )

    # Nulls
    null_count = int(df.isna().sum().sum())

    record_result(
        filename,
        "null_check",
        null_count == 0,
        f"Null values: {null_count}",
    )

    # Duplicates
    duplicate_count = int(df.duplicated().sum())

    record_result(
        filename,
        "duplicate_check",
        duplicate_count == 0,
        f"Duplicate rows: {duplicate_count}",
    )

    # Provenance
    if "provenance" in df.columns:

        valid_provenance = df["provenance"].eq("SYNTHETIC").all()

        record_result(
            filename,
            "provenance_check",
            valid_provenance,
            "All records labelled SYNTHETIC",
        )


# ------------------------------------------------------------
# Run basic checks
# ------------------------------------------------------------

for filename, df in datasets.items():
    check_dataset(filename, df)


# ------------------------------------------------------------
# Asset master checks
# ------------------------------------------------------------

assets = datasets["asset_master.csv"]

asset_ids = set(assets["asset_id"])

record_result(
    "asset_master.csv",
    "asset_id_uniqueness",
    assets["asset_id"].is_unique,
    f"Unique asset IDs: {assets['asset_id'].nunique()}",
)


# ------------------------------------------------------------
# Telemetry checks
# ------------------------------------------------------------

telemetry = datasets["asset_telemetry.csv"]

telemetry["timestamp"] = pd.to_datetime(
    telemetry["timestamp"],
    errors="coerce",
)

record_result(
    "asset_telemetry.csv",
    "timestamp_check",
    telemetry["timestamp"].notna().all(),
    "All timestamps successfully parsed",
)

record_result(
    "asset_telemetry.csv",
    "asset_reference_check",
    telemetry["asset_id"].isin(asset_ids).all(),
    "All telemetry asset IDs exist in asset master",
)

record_result(
    "asset_telemetry.csv",
    "pressure_range_check",
    (telemetry["pressure_bar"] >= 0).all(),
    "Pressure must be >= 0",
)

record_result(
    "asset_telemetry.csv",
    "flow_range_check",
    (telemetry["flow_rate_m3h"] >= 0).all(),
    "Flow rate must be >= 0",
)

record_result(
    "asset_telemetry.csv",
    "current_range_check",
    (telemetry["motor_current_a"] >= 0).all(),
    "Motor current must be >= 0",
)

record_result(
    "asset_telemetry.csv",
    "valve_position_check",
    telemetry["valve_position_pct"].between(0, 100).all(),
    "Valve position must be between 0 and 100%",
)

record_result(
    "asset_telemetry.csv",
    "failure_flag_check",
    telemetry["failure_flag"].isin([0, 1]).all(),
    "Failure flag must be 0 or 1",
)


# ------------------------------------------------------------
# Asset relationship checks
# ------------------------------------------------------------

relationships = datasets["asset_relationships.csv"]

relationship_ids = pd.concat(
    [
        relationships["pump_id"],
        relationships["valve_id"],
        relationships["loading_arm_id"],
    ]
)

record_result(
    "asset_relationships.csv",
    "asset_reference_check",
    relationship_ids.isin(asset_ids).all(),
    "All relationship asset IDs exist in asset master",
)


# ------------------------------------------------------------
# Loading operation checks
# ------------------------------------------------------------

loading = datasets["loading_operations.csv"]

loading["start_time"] = pd.to_datetime(
    loading["start_time"],
    errors="coerce",
)

loading["end_time"] = pd.to_datetime(
    loading["end_time"],
    errors="coerce",
)

record_result(
    "loading_operations.csv",
    "timestamp_check",
    loading["start_time"].notna().all()
    and loading["end_time"].notna().all(),
    "All operation timestamps successfully parsed",
)

record_result(
    "loading_operations.csv",
    "temporal_check",
    (loading["end_time"] >= loading["start_time"]).all(),
    "End time must be greater than or equal to start time",
)

record_result(
    "loading_operations.csv",
    "volume_check",
    (loading["volume_litres"] > 0).all(),
    "Loading volume must be greater than zero",
)

loading_asset_columns = [
    "loading_arm_id",
    "assigned_pump",
    "assigned_valve",
]

loading_reference_valid = all(
    loading[column].isin(asset_ids).all()
    for column in loading_asset_columns
)

record_result(
    "loading_operations.csv",
    "asset_reference_check",
    loading_reference_valid,
    "All assigned assets exist in asset master",
)


# ------------------------------------------------------------
# Maintenance checks
# ------------------------------------------------------------

maintenance = datasets["maintenance_work_orders.csv"]

maintenance["maintenance_start"] = pd.to_datetime(
    maintenance["maintenance_start"],
    errors="coerce",
)

maintenance["maintenance_end"] = pd.to_datetime(
    maintenance["maintenance_end"],
    errors="coerce",
)

record_result(
    "maintenance_work_orders.csv",
    "timestamp_check",
    maintenance["maintenance_start"].notna().all()
    and maintenance["maintenance_end"].notna().all(),
    "All maintenance timestamps successfully parsed",
)

record_result(
    "maintenance_work_orders.csv",
    "temporal_check",
    (maintenance["maintenance_end"] >= maintenance["maintenance_start"]).all(),
    "Maintenance end must be after start",
)

record_result(
    "maintenance_work_orders.csv",
    "asset_reference_check",
    maintenance["asset_id"].isin(asset_ids).all(),
    "All maintenance asset IDs exist in asset master",
)


# ------------------------------------------------------------
# Alarm checks
# ------------------------------------------------------------

alarms = datasets["alarm_events.csv"]

alarms["timestamp"] = pd.to_datetime(
    alarms["timestamp"],
    errors="coerce",
)

record_result(
    "alarm_events.csv",
    "timestamp_check",
    alarms["timestamp"].notna().all(),
    "All alarm timestamps successfully parsed",
)

record_result(
    "alarm_events.csv",
    "asset_reference_check",
    alarms["asset_id"].isin(asset_ids).all(),
    "All alarm asset IDs exist in asset master",
)


# ------------------------------------------------------------
# Save validated data
# ------------------------------------------------------------

for filename, df in datasets.items():

    output_path = PROCESSED_DIR / filename

    df.to_csv(output_path, index=False)


# ------------------------------------------------------------
# Save quality report
# ------------------------------------------------------------

report_path = QUALITY_DIR / "quality_report.json"

with open(report_path, "w", encoding="utf-8") as file:
    json.dump(report, file, indent=4, default=str)


# ------------------------------------------------------------
# Print summary
# ------------------------------------------------------------

print()
print("=" * 60)
print("MaintainNexusAI DATA QUALITY REPORT")
print("=" * 60)

for dataset, checks in report["datasets"].items():

    print(f"\n{dataset}")

    for check, result in checks.items():

        print(
            f"  {check:<30} {result['status']}"
        )


print()
print("=" * 60)
print(
    f"OVERALL DATA QUALITY: {report['overall_status']}"
)
print("=" * 60)

print()
print(f"Validated data: {PROCESSED_DIR}")
print(f"Quality report: {report_path}")


# ------------------------------------------------------------
# Fail pipeline if quality gate fails
# ------------------------------------------------------------

if report["overall_status"] != "PASS":

    raise SystemExit(
        "\nDATA QUALITY GATE FAILED. "
        "Review quality_report.json before continuing."
    )

print("\nDATA QUALITY GATE PASSED.")