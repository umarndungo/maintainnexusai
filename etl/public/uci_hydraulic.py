"""Extract cycle-level features and labels from UCI hydraulic systems data."""
from __future__ import annotations
from pathlib import Path
import zipfile
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "public_benchmarks"
OUT.mkdir(parents=True, exist_ok=True)

SENSORS = [
    "PS1", "PS2", "PS3", "PS4", "PS5", "PS6", "EPS1",
    "FS1", "FS2", "TS1", "TS2", "TS3", "TS4", "VS1", "CE", "CP", "SE"
]


def find_member(zf: zipfile.ZipFile, basename: str) -> str:
    for name in zf.namelist():
        if Path(name).name.lower() == basename.lower():
            return name
    raise FileNotFoundError(f"{basename} not found in hydraulic ZIP")


def read_matrix(zf: zipfile.ZipFile, member: str) -> np.ndarray:
    with zf.open(member) as fh:
        return np.loadtxt(fh, delimiter="\t")


def summarize(matrix: np.ndarray, prefix: str) -> pd.DataFrame:
    # Each row is a 60-second cycle. Columns are samples within that cycle.
    x = np.asarray(matrix, dtype=float)
    return pd.DataFrame({
        f"{prefix}_mean": np.nanmean(x, axis=1),
        f"{prefix}_std": np.nanstd(x, axis=1),
        f"{prefix}_min": np.nanmin(x, axis=1),
        f"{prefix}_max": np.nanmax(x, axis=1),
    })


def run(zip_path: Path | None = None) -> Path:
    zip_path = zip_path or (RAW / "uci_hydraulic_447.zip")
    if not zip_path.exists():
        raise FileNotFoundError(f"Missing {zip_path}. Run scripts/download_public_data.py first.")

    with zipfile.ZipFile(zip_path) as zf:
        pieces = []
        for sensor in SENSORS:
            member = find_member(zf, f"{sensor}.txt")
            matrix = read_matrix(zf, member)
            pieces.append(summarize(matrix, sensor))
        features = pd.concat(pieces, axis=1)

        profile_member = find_member(zf, "profile.txt")
        with zf.open(profile_member) as fh:
            profile = pd.read_csv(fh, sep="\t", header=None)

    profile.columns = ["cooler_condition", "valve_condition", "pump_leakage_level", "accumulator_pressure", "stable_flag"]
    df = pd.concat([features, profile], axis=1)
    df.insert(0, "cycle_id", np.arange(1, len(df) + 1))
    df["provenance"] = "EXTERNAL_PUBLIC"
    df["source_dataset"] = "uci_hydraulic_447"
    out = OUT / "uci_hydraulic_447_cycle_features.csv"
    df.to_csv(out, index=False)
    return out


if __name__ == "__main__":
    print(run())
