"""Canonical ETL for the predictive-maintenance prototype.

The ETL keeps external public benchmark data separate from synthetic KPC-style
operational data, then produces a clean canonical telemetry/label table for ML.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SYN = ROOT / "data" / "synthetic"
STAGE = ROOT / "data" / "staging"
PROC = ROOT / "data" / "processed"
STAGE.mkdir(parents=True, exist_ok=True)
PROC.mkdir(parents=True, exist_ok=True)


def run():
    equipment = pd.read_csv(SYN / "equipment_register.csv", parse_dates=["installation_date"])
    telemetry = pd.read_csv(SYN / "telemetry.csv", parse_dates=["timestamp"])
    maintenance = pd.read_csv(SYN / "maintenance_logs.csv", parse_dates=["maintenance_date"])

    df = telemetry.merge(equipment[["equipment_id", "criticality_score", "installation_date"]], on="equipment_id", how="left")
    df = df.sort_values(["equipment_id", "timestamp"])

    g = df.groupby("equipment_id", group_keys=False)
    df["vibration_roll_mean_24h"] = g["vibration_rms"].transform(lambda s: s.rolling(24, min_periods=3).mean())
    df["temperature_roll_mean_24h"] = g["temperature_c"].transform(lambda s: s.rolling(24, min_periods=3).mean())
    df["pressure_roll_std_24h"] = g["pressure_bar"].transform(lambda s: s.rolling(24, min_periods=3).std())
    df["days_since_installation"] = (df["timestamp"].dt.tz_localize(None) - df["installation_date"]).dt.total_seconds() / 86400

    failure_times = (maintenance.groupby("equipment_id", as_index=False)["maintenance_date"].min().rename(columns={"maintenance_date": "first_maintenance_date"}))
    df = df.merge(failure_times, on="equipment_id", how="left")
    df["failure_within_24h"] = df["failure_event"].astype(int)

    # Remove rows where rolling features are not yet available.
    feature_cols = ["vibration_roll_mean_24h", "temperature_roll_mean_24h", "pressure_roll_std_24h", "days_since_installation"]
    clean = df.dropna(subset=feature_cols).copy()
    clean.to_csv(STAGE / "canonical_telemetry_staged.csv", index=False)
    try:
        clean.to_parquet(PROC / "canonical_ml_dataset.parquet", index=False)
    except ImportError:
        # CSV remains the portable canonical artifact when parquet extras are absent.
        pass
    clean.to_csv(PROC / "canonical_ml_dataset.csv", index=False)
    print(f"Staged rows: {len(clean):,}")
    print(f"Output: {PROC / 'canonical_ml_dataset.csv'}")


if __name__ == "__main__":
    run()
