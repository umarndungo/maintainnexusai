"""Generate clearly labelled KPC-style prototype data.

This data is NOT KPC telemetry. It is synthetic data designed to exercise the
Predict -> Decide -> Act -> Learn architecture until authorized operational data
is available.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "synthetic"
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(42)

ASSETS = []
for i in range(1, 9):
    ASSETS.append((f"PUMP-{i:03d}", "PUMP", "DEPOT-A", 0.95 if i <= 2 else 0.75))
for i in range(1, 7):
    ASSETS.append((f"ARM-{i:03d}", "LOADING_ARM", "DEPOT-A", 0.85 if i <= 2 else 0.65))
for i in range(1, 13):
    ASSETS.append((f"VALVE-{i:03d}", "VALVE", "DEPOT-A", 0.80 if i <= 4 else 0.60))

asset_df = pd.DataFrame(ASSETS, columns=["equipment_id", "equipment_type", "depot", "criticality_score"])
asset_df["installation_date"] = pd.Timestamp("2019-01-01") + pd.to_timedelta(rng.integers(0, 1600, len(asset_df)), unit="D")
asset_df["rated_capacity_lph"] = np.where(asset_df.equipment_type.eq("PUMP"), rng.integers(150000, 350000, len(asset_df)), np.nan)
asset_df["rated_pressure_bar"] = np.where(asset_df.equipment_type.isin(["PUMP", "VALVE"]), rng.uniform(8, 18, len(asset_df)).round(2), np.nan)
asset_df.to_csv(OUT / "equipment_register.csv", index=False)

rows = []
start = pd.Timestamp("2026-01-01", tz="UTC")
for asset in asset_df.itertuples(index=False):
    n = 1200
    ts = pd.date_range(start, periods=n, freq="h")
    age = np.linspace(0, 1, n)
    degradation = np.maximum(0, age - rng.uniform(0.45, 0.75))
    if asset.equipment_type == "PUMP":
        vibration = 2.0 + 0.5 * rng.normal(size=n) + 5.0 * degradation
        temperature = 62 + 2.0 * rng.normal(size=n) + 18 * degradation
        pressure = 12 + rng.normal(0, .3, n) - 2.0 * degradation
        flow = 240000 + rng.normal(0, 5000, n) - 30000 * degradation
        current = 80 + rng.normal(0, 2, n) + 14 * degradation
        rpm = 1780 + rng.normal(0, 10, n) - 80 * degradation
        position = np.full(n, np.nan)
        actuator_pressure = np.full(n, np.nan)
    elif asset.equipment_type == "LOADING_ARM":
        vibration = 1.5 + rng.normal(0, .25, n) + 3.0 * degradation
        temperature = 48 + rng.normal(0, 1.5, n) + 10 * degradation
        pressure = 7 + rng.normal(0, .25, n) - 1.2 * degradation
        flow = 180000 + rng.normal(0, 4500, n) - 18000 * degradation
        current = 22 + rng.normal(0, 1, n) + 5 * degradation
        rpm = np.full(n, np.nan)
        position = np.clip(98 + rng.normal(0, .7, n) - 10 * degradation, 60, 100)
        actuator_pressure = 110 + rng.normal(0, 2, n) - 20 * degradation
    else:
        vibration = 0.8 + rng.normal(0, .15, n) + 1.5 * degradation
        temperature = 42 + rng.normal(0, 1, n) + 7 * degradation
        pressure = 9 + rng.normal(0, .2, n) - 1.5 * degradation
        flow = 0 + rng.normal(0, .2, n)
        current = 12 + rng.normal(0, .6, n) + 2 * degradation
        rpm = np.full(n, np.nan)
        position = np.clip(100 + rng.normal(0, .5, n) - 15 * degradation, 0, 100)
        actuator_pressure = 95 + rng.normal(0, 1.5, n) - 15 * degradation

    risk_signal = (
        (vibration > np.nanpercentile(vibration, 92)).astype(int)
        + (temperature > np.nanpercentile(temperature, 92)).astype(int)
        + (pressure < np.nanpercentile(pressure, 8)).astype(int)
    )
    failure = ((degradation > .35) & (risk_signal >= 1)).astype(int)
    for j in range(n):
        rows.append([
            ts[j], asset.equipment_id, asset.equipment_type,
            vibration[j], temperature[j], pressure[j], flow[j], current[j], rpm[j],
            position[j], actuator_pressure[j], int(j), failure[j]
        ])

telemetry = pd.DataFrame(rows, columns=[
    "timestamp", "equipment_id", "equipment_type", "vibration_rms",
    "temperature_c", "pressure_bar", "flow_lph", "motor_current_a", "rpm",
    "position_pct", "actuator_pressure_bar", "cycle_count", "failure_event"
])
telemetry.to_csv(OUT / "telemetry.csv", index=False)

failure_rows = telemetry.loc[telemetry.failure_event.eq(1), ["equipment_id", "equipment_type", "timestamp"]].copy()
failure_rows["failure_id"] = [f"FAIL-{i:06d}" for i in range(1, len(failure_rows) + 1)]
failure_rows["failure_mode"] = failure_rows.equipment_type.map({"PUMP": "BEARING_OR_PERFORMANCE_DEGRADATION", "LOADING_ARM": "ACTUATION_DEGRADATION", "VALVE": "ACTUATION_FAILURE"})
failure_rows["severity"] = "HIGH"
failure_rows["downtime_hours"] = rng.uniform(1, 12, len(failure_rows)).round(2)
failure_rows.to_csv(OUT / "failure_events.csv", index=False)

maintenance = failure_rows[["failure_id", "equipment_id", "equipment_type", "timestamp"]].copy()
maintenance.rename(columns={"timestamp": "maintenance_date"}, inplace=True)
maintenance["maintenance_type"] = "CORRECTIVE"
maintenance["technician_id"] = [f"TECH-{i%12+1:03d}" for i in range(len(maintenance))]
maintenance["repair_hours"] = rng.uniform(1, 10, len(maintenance)).round(2)
maintenance["part_number"] = maintenance.equipment_type.map({"PUMP": "PUMP-SEAL-KIT", "LOADING_ARM": "ARM-ACTUATOR-KIT", "VALVE": "VALVE-ACTUATOR-KIT"})
maintenance.to_csv(OUT / "maintenance_logs.csv", index=False)

loading_points = []
for i in range(1, 9):
    equipment_id = f"PUMP-{(i % 8) + 1:03d}"
    loading_points.append((f"LP-{i:03d}", equipment_id, "AVAILABLE", int(rng.integers(150000, 300000))))
pd.DataFrame(loading_points, columns=["loading_point_id", "equipment_id", "status", "capacity_lph"]).to_csv(OUT / "loading_points.csv", index=False)

trucks = []
for i in range(1, 401):
    trucks.append((f"TRUCK-{i:05d}", start + pd.Timedelta(hours=int(rng.integers(0, 1200))), f"LP-{rng.integers(1,9):03d}", int(rng.integers(15000, 45000)), rng.choice(["NORMAL", "PRIORITY"])))
pd.DataFrame(trucks, columns=["truck_id", "scheduled_time", "loading_point_id", "planned_volume_l", "priority"]).to_csv(OUT / "truck_schedule.csv", index=False)

spares = pd.DataFrame([
    ["PUMP-SEAL-KIT", "Pump seal kit", 4, 2, 21],
    ["ARM-ACTUATOR-KIT", "Loading arm actuator kit", 2, 1, 30],
    ["VALVE-ACTUATOR-KIT", "Valve actuator kit", 3, 1, 28],
], columns=["part_number", "part_name", "quantity_available", "reorder_level", "lead_time_days"])
spares.to_csv(OUT / "spare_parts.csv", index=False)

print(f"Generated synthetic prototype data in {OUT}")
print(f"Assets: {len(asset_df):,}; telemetry rows: {len(telemetry):,}; failures: {len(failure_rows):,}")
