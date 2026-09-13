"""Download public predictive-maintenance sources into data/raw."""

from __future__ import annotations

import argparse
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "uci_ai4i_2020": (
        "https://archive.ics.uci.edu/static/public/601/ai4i%2B2020%2Bpredictive%2Bmaintenance%2Bdataset.zip",
        RAW / "uci_ai4i_2020.zip",
    ),
    "uci_hydraulic_447": (
        "https://archive.ics.uci.edu/static/public/447/condition+monitoring+of+hydraulic+systems.zip",
        RAW / "uci_hydraulic_447.zip",
    ),
}


def download(name: str) -> None:
    url, destination = SOURCES[name]

    print(f"Downloading {name}")
    print(f"URL: {url}")
    print(f"Destination: {destination}")

    temp_file = destination.with_suffix(".download")

    if temp_file.exists():
        temp_file.unlink()

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        total = response.headers.get("Content-Length")
        total = int(total) if total else None

        downloaded = 0

        with open(temp_file, "wb") as output:
            while True:
                chunk = response.read(1024 * 1024)

                if not chunk:
                    break

                output.write(chunk)
                downloaded += len(chunk)

                if total:
                    percent = downloaded / total * 100
                    print(
                        f"\rProgress: {percent:6.2f}% "
                        f"({downloaded:,}/{total:,} bytes)",
                        end="",
                        flush=True,
                    )
                else:
                    print(
                        f"\rDownloaded: {downloaded:,} bytes",
                        end="",
                        flush=True,
                    )

    print()

    if not temp_file.exists() or temp_file.stat().st_size == 0:
        raise RuntimeError(f"Download failed for {name}.")

    if not zipfile.is_zipfile(temp_file):
        temp_file.unlink()
        raise RuntimeError(
            f"Downloaded file for {name} is not a valid ZIP archive."
        )

    shutil.move(str(temp_file), str(destination))

    print(
        f"Saved {destination} "
        f"({destination.stat().st_size:,} bytes)"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        choices=["all", *SOURCES],
        required=True,
    )

    args = parser.parse_args()

    names = list(SOURCES) if args.source == "all" else [args.source]

    for name in names:
        download(name)


if __name__ == "__main__":
    main()