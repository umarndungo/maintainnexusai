"""Extract and normalize the UCI AI4I 2020 benchmark.

The dataset is synthetic and is kept as EXTERNAL_PUBLIC benchmark data.
It is not merged with KPC-style synthetic operational telemetry.
"""
from __future__ import annotations
from pathlib import Path
import zipfile
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "public_benchmarks"
OUT.mkdir(parents=True, exist_ok=True)


def locate_csv(zf: zipfile.ZipFile) -> str:
    candidates = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    for n in candidates:
        if "ai4i" in n.lower():
            return n
    if len(candidates) == 1:
        return candidates[0]
    raise FileNotFoundError("Could not uniquely identify AI4I CSV in ZIP")


def run(zip_path: Path | None = None) -> Path:
    zip_path = zip_path or (RAW / "uci_ai4i_2020.zip")
    if not zip_path.exists():
        raise FileNotFoundError(f"Missing {zip_path}. Run scripts/download_public_data.py first.")
    with zipfile.ZipFile(zip_path) as zf:
        name = locate_csv(zf)
        with zf.open(name) as fh:
            df = pd.read_csv(fh)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    rename = {
        "air_temperature_[k]": "air_temperature_k",
        "process_temperature_[k]": "process_temperature_k",
        "rotational_speed_[rpm]": "rotational_speed_rpm",
        "torque_[nm]": "torque_nm",
        "tool_wear_[min]": "tool_wear_min",
        "machine_failure": "machine_failure",
    }
    df = df.rename(columns=rename)
    df["provenance"] = "EXTERNAL_PUBLIC"
    df["source_dataset"] = "uci_ai4i_2020"
    out = OUT / "uci_ai4i_2020_normalized.csv"
    df.to_csv(out, index=False)
    return out


if __name__ == "__main__":
    print(run())
