from pathlib import Path
import random

import numpy as np
import pandas as pd


# ============================================================
# MaintainNexusAI
# Synthetic KPC-like Operational Data Generator
#
# IMPORTANT:
# All generated data is SYNTHETIC.
# It must NOT be represented as actual KPC data.
# ============================================================

random.seed(42)
np.random.seed(42)


# ------------------------------------------------------------
# Directories
# ------------------------------------------------------------

OUTPUT_DIR = Path("data/raw/synthetic_kpc")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

START_DATE = "2026-01-01"
TELEMETRY_DAYS = 30
TELEMETRY_INTERVAL_MINUTES = 1

ASSET_COUNT = 48

TELEMETRY_RECORDS = (
    TELEMETRY_DAYS
    * 24
    * 60
    * ASSET_COUNT
)
# ============================================================
# 1. ASSET MASTER
# ============================================================

assets = []

# 12 stations
stations = [f"ST{i:02d}" for i in range(1, 13)]

# 12 pumps
for i in range(1, 13):
    station = stations[i - 1]

    assets.append({
        "asset_id": f"PUMP-{i:03d}",
        "asset_type": "PUMP",
        "station_id": station,
        "location": f"Station {station}",
        "criticality": "CRITICAL",
        "status": "ACTIVE",
        "provenance": "SYNTHETIC",
    })


# 24 valves
for i in range(1, 25):
    station = stations[(i - 1) % 12]

    assets.append({
        "asset_id": f"VALVE-{i:03d}",
        "asset_type": "VALVE",
        "station_id": station,
        "location": f"Station {station}",
        "criticality": "HIGH",
        "status": "ACTIVE",
        "provenance": "SYNTHETIC",
    })


# 12 loading arms
for i in range(1, 13):
    station = stations[i - 1]

    assets.append({
        "asset_id": f"ARM-{i:03d}",
        "asset_type": "LOADING_ARM",
        "station_id": station,
        "location": f"Station {station}",
        "criticality": "HIGH",
        "status": "ACTIVE",
        "provenance": "SYNTHETIC",
    })


asset_master = pd.DataFrame(assets)

asset_master.to_csv(
    OUTPUT_DIR / "asset_master.csv",
    index=False,
)

print(f"[1/6] Asset master: {len(asset_master)} rows")


# ============================================================
# 2. ASSET RELATIONSHIPS
# ============================================================

relationships = []

for i in range(1, 13):

    station = stations[i - 1]

    relationships.append({
        "pump_id": f"PUMP-{i:03d}",
        "valve_id": f"VALVE-{i:03d}",
        "loading_arm_id": f"ARM-{i:03d}",
        "station_id": station,
        "relationship_type": "PRIMARY_FLOW_PATH",
        "provenance": "SYNTHETIC",
    })


asset_relationships = pd.DataFrame(relationships)

asset_relationships.to_csv(
    OUTPUT_DIR / "asset_relationships.csv",
    index=False,
)

print(
    f"[2/6] Asset relationships: "
    f"{len(asset_relationships)} rows"
)


# ============================================================
# 3. ASSET TELEMETRY
#
# IMPORTANT CHANGE:
# Telemetry is generated for ALL 48 assets:
#
#   12 PUMPS
#   24 VALVES
#   12 LOADING ARMS
#
# Each asset type has different operating characteristics.
# ============================================================

asset_ids = asset_master["asset_id"].tolist()

# We distribute records evenly across all assets.
records_per_asset = TELEMETRY_RECORDS // len(asset_ids)

timestamps = pd.date_range(
    start=START_DATE,
    periods=records_per_asset,
    freq="1min",
)

telemetry_records = []

for _, asset in asset_master.iterrows():

    asset_id = asset["asset_id"]
    asset_type = asset["asset_type"]

    # --------------------------------------------------------
    # Base operating ranges by asset type
    # --------------------------------------------------------

    if asset_type == "PUMP":

        base_pressure = 8.0
        base_temperature = 55.0
        base_flow = 110.0
        base_current = 48.0
        base_vibration = 2.5
        base_valve_position = 100.0

        failure_types = [
            "PUMP_LEAK",
            "OVERHEATING",
            "HIGH_VIBRATION",
        ]

    elif asset_type == "VALVE":

        base_pressure = 7.5
        base_temperature = 48.0
        base_flow = 105.0
        base_current = 0.0
        base_vibration = 1.5
        base_valve_position = 85.0

        failure_types = [
            "VALVE_STICKING",
            "FLOW_DEVIATION",
            "SEAL_WEAR",
        ]

    else:

        base_pressure = 7.0
        base_temperature = 45.0
        base_flow = 100.0
        base_current = 0.0
        base_vibration = 2.0
        base_valve_position = 90.0

        failure_types = [
            "SEAL_WEAR",
            "HIGH_VIBRATION",
            "FLOW_DEVIATION",
        ]


    # --------------------------------------------------------
    # Generate telemetry records
    # --------------------------------------------------------

        # --------------------------------------------------------
    # Multiple synthetic failure events
    #
    # Each asset experiences several failure cycles across
    # the 30-day telemetry period.
    #
    # Events are intentionally separated by more than 48h
    # so that the prediction horizon can be evaluated cleanly.
    # --------------------------------------------------------

    event_positions = [
        int(len(timestamps) * 0.15),
        int(len(timestamps) * 0.40),
        int(len(timestamps) * 0.65),
        int(len(timestamps) * 0.85),
    ]

    failure_events = []

    for event_position in event_positions:

        # Add small random variation to event timing
        jitter = random.randint(
            -360,
            360,
        )

        event_start = max(
            180,
            min(
                len(timestamps) - 30,
                event_position + jitter,
            ),
        )

        event_duration = random.randint(
            5,
            15,
        )

        event_end = (
            event_start
            + event_duration
        )

        event_type = random.choice(
            failure_types
        )

        failure_events.append({
            "start": event_start,
            "end": event_end,
            "type": event_type,
        })

    for timestamp_index, timestamp in enumerate(timestamps):
        operating_state = random.choices(
            ["LOADING", "IDLE"],
            weights=[0.62, 0.38],
            k=1,
        )[0]


                # ----------------------------------------------------
        # Event-based synthetic degradation
        #
        # The asset follows repeated cycles:
        #
        # NORMAL
        #    ↓
        # DEGRADATION
        #    ↓
        # FAILURE
        #    ↓
        # RECOVERY
        #
        # Only historical/current telemetry is used to create
        # the sensor values. The future target is generated
        # separately by build_failure_target.py.
        # ----------------------------------------------------

        failure_flag = 0
        failure_type = "NONE"

        degradation = np.random.uniform(
            0.02,
            0.12,
        )

        # Check every failure event
        for event in failure_events:

            event_start = event["start"]
            event_end = event["end"]

            # ------------------------------------------------
            # 2-hour degradation period before failure
            # ------------------------------------------------

            if (
                timestamp_index >= event_start - 120
                and timestamp_index < event_start
            ):

                progress = (
                    timestamp_index
                    - (event_start - 120)
                ) / 120

                degradation = (
                    0.12
                    + (progress * 0.70)
                    + np.random.normal(0, 0.03)
                )

                degradation = max(
                    0.05,
                    min(0.90, degradation),
                )

            # ------------------------------------------------
            # Actual failure event
            # ------------------------------------------------

            elif (
                timestamp_index >= event_start
                and timestamp_index < event_end
            ):

                degradation = np.random.uniform(
                    0.85,
                    1.0,
                )

                failure_flag = 1
                failure_type = event["type"]

            # ------------------------------------------------
            # Recovery period immediately after failure
            # ------------------------------------------------

            elif (
                timestamp_index >= event_end
                and timestamp_index < event_end + 120
            ):

                recovery_progress = (
                    timestamp_index - event_end
                ) / 120

                degradation = (
                    0.80
                    - (recovery_progress * 0.65)
                    + np.random.normal(0, 0.03)
                )

                degradation = max(
                    0.05,
                    min(0.80, degradation),
                )

        # ----------------------------------------------------
        # Sensor behavior
        # ----------------------------------------------------

        pressure = (
            base_pressure
            - (degradation * 3.5)
            + np.random.normal(0, 0.25)
        )

        temperature = (
            base_temperature
            + (degradation * 25)
            + np.random.normal(0, 1.5)
        )

        flow_rate = (
            base_flow
            - (degradation * 40)
            + np.random.normal(0, 4)
        )

        motor_current = (
            base_current
            + (degradation * 18)
            + np.random.normal(0, 2)
        )

        vibration = (
            base_vibration
            + (degradation * 8)
            + np.random.normal(0, 0.35)
        )

        valve_position = (
            base_valve_position
            - (degradation * 35)
            + np.random.normal(0, 2)
        )


        # ----------------------------------------------------
        # Idle equipment has lower flow
        # ----------------------------------------------------

        if operating_state == "IDLE":

            flow_rate *= np.random.uniform(
                0.05,
                0.25,
            )

            if asset_type != "PUMP":
                valve_position *= np.random.uniform(
                    0.05,
                    0.30,
                )


        # ----------------------------------------------------
        # Keep physical values within reasonable ranges
        # ----------------------------------------------------

        pressure = max(0, pressure)
        temperature = max(0, temperature)
        flow_rate = max(0, flow_rate)
        motor_current = max(0, motor_current)
        vibration = max(0, vibration)
        valve_position = min(
            100,
            max(0, valve_position),
        )


        

        # ----------------------------------------------------
        # Alarm generation
        # ----------------------------------------------------

        alarm_code = "NONE"

        if vibration > (
            base_vibration + 4
        ):

            alarm_code = "HIGH_VIBRATION"

        elif temperature > (
            base_temperature + 18
        ):

            alarm_code = "HIGH_TEMPERATURE"

        elif pressure < (
            base_pressure - 2.5
        ):

            alarm_code = "LOW_PRESSURE"

        elif flow_rate < (
            base_flow * 0.55
        ) and operating_state == "LOADING":

            alarm_code = "FLOW_DEVIATION"

        elif (
            asset_type in ["VALVE", "LOADING_ARM"]
            and valve_position < 50
            and operating_state == "LOADING"
        ):

            alarm_code = "VALVE_POSITION_DEVIATION"


        telemetry_records.append({

            "timestamp": timestamp,

            "asset_id": asset_id,

            "asset_type": asset_type,

            "pressure_bar": round(
                pressure,
                3,
            ),

            "temperature_c": round(
                temperature,
                3,
            ),

            "flow_rate_m3h": round(
                flow_rate,
                3,
            ),

            "motor_current_a": round(
                motor_current,
                3,
            ),

            "vibration_mm_s": round(
                vibration,
                3,
            ),

            "valve_position_pct": round(
                valve_position,
                3,
            ),

            "operating_state": operating_state,

            "alarm_code": alarm_code,

            "failure_flag": failure_flag,

            "failure_type": failure_type,

            "provenance": "SYNTHETIC",
        })


asset_telemetry = pd.DataFrame(
    telemetry_records
)

asset_telemetry.to_csv(
    OUTPUT_DIR / "asset_telemetry.csv",
    index=False,
)

print(
    f"[3/6] Asset telemetry: "
    f"{len(asset_telemetry):,} rows"
)

print(
    "      Telemetry by asset type:"
)

print(
    asset_telemetry["asset_type"]
    .value_counts()
    .to_string()
)


# ============================================================
# 4. LOADING OPERATIONS
# ============================================================

loading_operations = []

products = [
    "PETROL",
    "DIESEL",
    "JET_A1",
]

operation_timestamps = pd.date_range(
    start=START_DATE,
    periods=12000,
    freq="15min",
)


for i in range(12000):

    start_time = operation_timestamps[i]

    duration_minutes = random.randint(
        20,
        90,
    )

    end_time = (
        start_time
        + pd.Timedelta(
            minutes=duration_minutes
        )
    )

    arm_number = random.randint(
        1,
        12,
    )

    loading_operations.append({

        "loading_operation_id":
            f"LOAD-{i + 1:06d}",

        "start_time":
            start_time,

        "end_time":
            end_time,

        "truck_id":
            f"TRUCK-{random.randint(1, 500):04d}",

        "loading_arm_id":
            f"ARM-{arm_number:03d}",

        "assigned_pump":
            f"PUMP-{arm_number:03d}",

        "assigned_valve":
            f"VALVE-{arm_number:03d}",

        "product":
            random.choice(products),

        "volume_litres":
            random.randint(
                5000,
                45000,
            ),

        "operation_status":
            random.choices(
                [
                    "COMPLETED",
                    "INTERRUPTED",
                    "CANCELLED",
                ],
                weights=[
                    0.88,
                    0.08,
                    0.04,
                ],
                k=1,
            )[0],

        "provenance":
            "SYNTHETIC",
    })


loading_operations = pd.DataFrame(
    loading_operations
)

loading_operations.to_csv(
    OUTPUT_DIR / "loading_operations.csv",
    index=False,
)

print(
    f"[4/6] Loading operations: "
    f"{len(loading_operations):,} rows"
)


# ============================================================
# 5. MAINTENANCE WORK ORDERS
# ============================================================

maintenance_records = []

maintenance_failure_types = [
    "PUMP_LEAK",
    "HIGH_VIBRATION",
    "OVERHEATING",
    "VALVE_STICKING",
    "SEAL_WEAR",
    "INSPECTION",
]

maintenance_actions = [
    "REPAIR",
    "REPLACE_PART",
    "LUBRICATION",
    "CALIBRATION",
    "INSPECTION",
]

maintenance_types = [
    "CORRECTIVE",
    "PREVENTIVE",
]


for i in range(3000):

    asset_id = random.choice(
        asset_ids
    )

    start_time = pd.Timestamp(
        START_DATE
    ) + pd.Timedelta(
        minutes=random.randint(
            0,
            9 * 30 * 24 * 60,
        )
    )

    duration_hours = random.randint(
        1,
        24,
    )

    end_time = (
        start_time
        + pd.Timedelta(
            hours=duration_hours
        )
    )

    maintenance_records.append({

        "work_order_id":
            f"WO-{i + 1:06d}",

        "asset_id":
            asset_id,

        "maintenance_start":
            start_time,

        "maintenance_end":
            end_time,

        "failure_type":
            random.choice(
                maintenance_failure_types
            ),

        "maintenance_type":
            random.choice(
                maintenance_types
            ),

        "maintenance_action":
            random.choice(
                maintenance_actions
            ),

        "technician":
            f"TECH-{random.randint(1, 30):03d}",

        "resolution":
            random.choice(
                [
                    "RESOLVED",
                    "PART_REPLACED",
                    "CALIBRATED",
                    "INSPECTED",
                ]
            ),

        "provenance":
            "SYNTHETIC",
    })


maintenance_work_orders = pd.DataFrame(
    maintenance_records
)

maintenance_work_orders.to_csv(
    OUTPUT_DIR / "maintenance_work_orders.csv",
    index=False,
)

print(
    f"[5/6] Maintenance work orders: "
    f"{len(maintenance_work_orders):,} rows"
)


# ============================================================
# 6. ALARM EVENTS
# ============================================================

alarm_codes = [
    "HIGH_VIBRATION",
    "HIGH_TEMPERATURE",
    "LOW_PRESSURE",
    "FLOW_DEVIATION",
    "VALVE_POSITION_DEVIATION",
]

alarm_records = []

for i in range(8000):

    asset_id = random.choice(
        asset_ids
    )

    alarm_records.append({

        "alarm_id":
            f"ALARM-{i + 1:06d}",

        "timestamp":
            pd.Timestamp(
                START_DATE
            ) + pd.Timedelta(
                minutes=random.randint(
                    0,
                    9 * 30 * 24 * 60,
                )
            ),

        "asset_id":
            asset_id,

        "alarm_code":
            random.choice(
                alarm_codes
            ),

        "severity":
            random.choice(
                [
                    "LOW",
                    "MEDIUM",
                    "HIGH",
                    "CRITICAL",
                ]
            ),

        "status":
            random.choice(
                [
                    "OPEN",
                    "ACKNOWLEDGED",
                    "CLOSED",
                ]
            ),

        "provenance":
            "SYNTHETIC",
    })


alarm_events = pd.DataFrame(
    alarm_records
)

alarm_events.to_csv(
    OUTPUT_DIR / "alarm_events.csv",
    index=False,
)

print(
    f"[6/6] Alarm events: "
    f"{len(alarm_events):,} rows"
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("=" * 60)
print("SYNTHETIC DATA GENERATION COMPLETE")
print("=" * 60)

print()
print(
    f"Output directory:\n{OUTPUT_DIR}"
)

print()
print("Files created:")

for file in sorted(
    OUTPUT_DIR.glob("*.csv")
):

    df = pd.read_csv(file)

    print(
        f"  {file.name:<35}"
        f"{len(df):>8,} rows"
    )

print()
print(
    "Telemetry coverage:"
)

print(
    asset_telemetry
    .groupby("asset_type")
    .size()
    .to_string()
)

print()
print(
    "Failure distribution:"
)

print(
    asset_telemetry
    .groupby(
        ["asset_type", "failure_flag"]
    )
    .size()
    .to_string()
)

print()
print("IMPORTANT:")
print(
    "All generated records are labelled SYNTHETIC."
)
print(
    "They must not be represented as actual KPC data."
)