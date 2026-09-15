from pathlib import Path
import pandas as pd
import numpy as np

# ============================================================
# MaintainNexusAI - Synthetic KPC-like Operational Data
# ============================================================
# IMPORTANT:
# This data is SYNTHETIC prototype data.
# It is NOT real KPC operational data.
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "raw" / "synthetic_kpc"
OUTPUT.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(42)

print("=" * 60)
print("MaintainNexusAI Synthetic Data Generator")
print("=" * 60)


# ------------------------------------------------------------
# 1. ASSET MASTER
# ------------------------------------------------------------

assets = []

# Pumps
for i in range(1, 13):
    station = f"STN-{((i - 1) % 3) + 1:02d}"
    assets.append([
        f"PMP-{i:03d}",
        "PUMP",
        station,
        f"TankFarm-{((i - 1) % 3) + 1}",
        "CRITICAL",
        "ACTIVE",
        "SYNTHETIC"
    ])

# Valves
for i in range(1, 25):
    station = f"STN-{((i - 1) % 3) + 1:02d}"
    assets.append([
        f"VLV-{i:03d}",
        "VALVE",
        station,
        f"TankFarm-{((i - 1) % 3) + 1}",
        "HIGH",
        "ACTIVE",
        "SYNTHETIC"
    ])

# Loading arms
for i in range(1, 13):
    station = f"STN-{((i - 1) % 3) + 1:02d}"
    assets.append([
        f"LARM-{i:03d}",
        "LOADING_ARM",
        station,
        f"Bay-{((i - 1) % 6) + 1}",
        "HIGH",
        "ACTIVE",
        "SYNTHETIC"
    ])

asset_df = pd.DataFrame(
    assets,
    columns=[
        "asset_id",
        "asset_type",
        "station_id",
        "location",
        "criticality",
        "status",
        "provenance"
    ]
)

asset_df.to_csv(
    OUTPUT / "asset_master.csv",
    index=False
)

print(f"[1/6] Asset master: {len(asset_df):,} rows")


# ------------------------------------------------------------
# 2. ASSET RELATIONSHIPS
# ------------------------------------------------------------

relationships = []

for station in ["STN-01", "STN-02", "STN-03"]:

    pumps = asset_df[
        (asset_df["station_id"] == station) &
        (asset_df["asset_type"] == "PUMP")
    ]["asset_id"].tolist()

    valves = asset_df[
        (asset_df["station_id"] == station) &
        (asset_df["asset_type"] == "VALVE")
    ]["asset_id"].tolist()

    arms = asset_df[
        (asset_df["station_id"] == station) &
        (asset_df["asset_type"] == "LOADING_ARM")
    ]["asset_id"].tolist()

    for i, arm in enumerate(arms):

        pump = pumps[i % len(pumps)]
        valve = valves[(i * 2) % len(valves)]

        relationships.append([
            pump,
            valve,
            arm,
            station,
            "PRIMARY_FLOW_PATH",
            "SYNTHETIC"
        ])

relationship_df = pd.DataFrame(
    relationships,
    columns=[
        "pump_id",
        "valve_id",
        "loading_arm_id",
        "station_id",
        "relationship_type",
        "provenance"
    ]
)

relationship_df.to_csv(
    OUTPUT / "asset_relationships.csv",
    index=False
)

print(f"[2/6] Asset relationships: {len(relationship_df):,} rows")


# ------------------------------------------------------------
# 3. ASSET TELEMETRY
# ------------------------------------------------------------

N_TELEMETRY = 60_000

timestamps = pd.date_range(
    start="2026-01-01",
    periods=N_TELEMETRY,
    freq="5min"
)

pump_ids = asset_df[
    asset_df["asset_type"] == "PUMP"
]["asset_id"].tolist()

telemetry = []

for timestamp in timestamps:

    pump = rng.choice(pump_ids)

    # Most observations are normal.
    degradation = 0.0

    # Approximately 10% of observations represent degradation.
    if rng.random() < 0.10:
        degradation = rng.uniform(0.5, 1.5)

    pressure = (
        5.8
        + rng.normal(0, 0.35)
        - degradation * 0.9
    )

    temperature = (
        48
        + rng.normal(0, 2.2)
        + degradation * 8
    )

    flow = (
        105
        + rng.normal(0, 5)
        - degradation * 14
    )

    motor_current = (
        72
        + rng.normal(0, 4)
        + degradation * 10
    )

    vibration = (
        2.1
        + abs(rng.normal(0, 0.45))
        + degradation * 2.8
    )

    valve_position = np.clip(
        92
        + rng.normal(0, 3)
        - degradation * 12,
        0,
        100
    )

    failure_flag = int(degradation > 1.25)

    if failure_flag:
        failure_type = "PUMP_LEAK"
        alarm_code = "HIGH_VIBRATION"
    elif vibration > 5.5:
        failure_type = "NONE"
        alarm_code = "HIGH_VIBRATION"
    elif temperature > 60:
        failure_type = "NONE"
        alarm_code = "HIGH_TEMPERATURE"
    else:
        failure_type = "NONE"
        alarm_code = "NONE"

    operating_state = (
        "LOADING"
        if rng.random() < 0.62
        else "IDLE"
    )

    telemetry.append([
        timestamp,
        pump,
        "PUMP",
        round(pressure, 3),
        round(temperature, 3),
        round(max(flow, 0), 3),
        round(max(motor_current, 0), 3),
        round(vibration, 3),
        round(valve_position, 3),
        operating_state,
        alarm_code,
        failure_flag,
        failure_type,
        "SYNTHETIC"
    ])

telemetry_df = pd.DataFrame(
    telemetry,
    columns=[
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
        "provenance"
    ]
)

telemetry_df.to_csv(
    OUTPUT / "asset_telemetry.csv",
    index=False
)

print(f"[3/6] Asset telemetry: {len(telemetry_df):,} rows")


# ------------------------------------------------------------
# 4. LOADING OPERATIONS
# ------------------------------------------------------------

N_OPERATIONS = 12_000

arms = asset_df[
    asset_df["asset_type"] == "LOADING_ARM"
]["asset_id"].tolist()

products = [
    "PETROL",
    "DIESEL",
    "JET_A1"
]

operations = []

for i in range(1, N_OPERATIONS + 1):

    start_time = (
        pd.Timestamp("2026-01-01")
        + pd.Timedelta(
            minutes=int(
                rng.integers(
                    0,
                    240 * 24 * 60
                )
            )
        )
    )

    duration = int(
        rng.integers(25, 150)
    )

    end_time = (
        start_time
        + pd.Timedelta(minutes=duration)
    )

    loading_arm = rng.choice(arms)

    relationship = relationship_df[
        relationship_df["loading_arm_id"] == loading_arm
    ].iloc[0]

    operation_status = rng.choice(
        [
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",
            "INTERRUPTED",
            "CANCELLED"
        ]
    )

    operations.append([
        f"LOAD-{i:06d}",
        start_time,
        end_time,
        f"TRK-{rng.integers(1, 801):04d}",
        loading_arm,
        relationship["pump_id"],
        relationship["valve_id"],
        rng.choice(products),
        int(rng.integers(5_000, 35_001)),
        operation_status,
        "SYNTHETIC"
    ])

operations_df = pd.DataFrame(
    operations,
    columns=[
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
        "provenance"
    ]
)

operations_df.to_csv(
    OUTPUT / "loading_operations.csv",
    index=False
)

print(f"[4/6] Loading operations: {len(operations_df):,} rows")


# ------------------------------------------------------------
# 5. MAINTENANCE WORK ORDERS
# ------------------------------------------------------------

N_WORK_ORDERS = 3_000

all_assets = asset_df[
    "asset_id"
].tolist()

failure_types = [
    "PUMP_LEAK",
    "HIGH_VIBRATION",
    "OVERHEATING",
    "VALVE_STICKING",
    "SEAL_WEAR",
    "INSPECTION"
]

maintenance_actions = [
    "REPAIR",
    "REPLACE_PART",
    "LUBRICATION",
    "CALIBRATION",
    "INSPECTION"
]

work_orders = []

for i in range(1, N_WORK_ORDERS + 1):

    start_time = (
        pd.Timestamp("2026-01-01")
        + pd.Timedelta(
            minutes=int(
                rng.integers(
                    0,
                    240 * 24 * 60
                )
            )
        )
    )

    duration_hours = int(
        rng.integers(1, 12)
    )

    end_time = (
        start_time
        + pd.Timedelta(hours=duration_hours)
    )

    work_orders.append([
        f"WO-{i:06d}",
        rng.choice(all_assets),
        start_time,
        end_time,
        rng.choice(failure_types),
        rng.choice([
            "CORRECTIVE",
            "PREVENTIVE"
        ]),
        rng.choice(maintenance_actions),
        f"TECH-{rng.integers(1, 31):03d}",
        rng.choice([
            "RESOLVED",
            "MONITOR",
            "PARTS_PENDING"
        ]),
        "SYNTHETIC"
    ])

work_orders_df = pd.DataFrame(
    work_orders,
    columns=[
        "work_order_id",
        "asset_id",
        "maintenance_start",
        "maintenance_end",
        "failure_type",
        "maintenance_type",
        "maintenance_action",
        "technician",
        "resolution",
        "provenance"
    ]
)

work_orders_df.to_csv(
    OUTPUT / "maintenance_work_orders.csv",
    index=False
)

print(f"[5/6] Maintenance work orders: {len(work_orders_df):,} rows")


# ------------------------------------------------------------
# 6. ALARM EVENTS
# ------------------------------------------------------------

N_ALARMS = 8_000

alarm_codes = [
    "HIGH_VIBRATION",
    "HIGH_TEMPERATURE",
    "LOW_PRESSURE",
    "FLOW_DEVIATION",
    "VALVE_POSITION_DEVIATION"
]

alarm_events = []

for i in range(1, N_ALARMS + 1):

    timestamp = (
        pd.Timestamp("2026-01-01")
        + pd.Timedelta(
            minutes=int(
                rng.integers(
                    0,
                    240 * 24 * 60
                )
            )
        )
    )

    alarm_events.append([
        f"ALM-{i:06d}",
        timestamp,
        rng.choice(all_assets),
        rng.choice(alarm_codes),
        rng.choice([
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL"
        ]),
        rng.choice([
            "OPEN",
            "ACKNOWLEDGED",
            "CLEARED"
        ]),
        "SYNTHETIC"
    ])

alarm_df = pd.DataFrame(
    alarm_events,
    columns=[
        "alarm_id",
        "timestamp",
        "asset_id",
        "alarm_code",
        "severity",
        "status",
        "provenance"
    ]
)

alarm_df.to_csv(
    OUTPUT / "alarm_events.csv",
    index=False
)

print(f"[6/6] Alarm events: {len(alarm_df):,} rows")


# ------------------------------------------------------------
# FINAL SUMMARY
# ------------------------------------------------------------

print()
print("=" * 60)
print("SYNTHETIC DATA GENERATION COMPLETE")
print("=" * 60)

print(f"Output directory:")
print(OUTPUT)

print()
print("Files created:")

for file in sorted(OUTPUT.glob("*.csv")):
    df = pd.read_csv(file)
    print(f"  {file.name:<35} {len(df):>8,} rows")

print()
print("IMPORTANT:")
print("All generated records are labelled SYNTHETIC.")
print("They must not be represented as actual KPC data.")