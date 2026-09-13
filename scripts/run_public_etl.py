"""Run public benchmark extraction after the source ZIPs are downloaded."""
from __future__ import annotations
import argparse

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from etl.public.uci_ai4i import run as run_ai4i
from etl.public.uci_hydraulic import run as run_hydraulic


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["all", "ai4i", "hydraulic"], default="all")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.source in {"all", "ai4i"}:
        print(f"AI4I -> {run_ai4i(root / 'data/raw/uci_ai4i_2020.zip')}")
    if args.source in {"all", "hydraulic"}:
        print(f"Hydraulic -> {run_hydraulic(root / 'data/raw/uci_hydraulic_447.zip')}")


if __name__ == "__main__":
    main()
