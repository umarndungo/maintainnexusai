# Data workspace

Raw, staging, processed and synthetic datasets are intentionally excluded from Git history.

## Reproduce

1. Download public sources:
   `python scripts/download_public_data.py --source all`
2. Generate prototype operational data:
   `python scripts/generate_synthetic_operational_data.py`
3. Run canonical ETL:
   `python scripts/run_ml_etl.py`

## Provenance

See `data/sources.yaml` and `docs/11-DATA-SOURCING-AND-ETL.md`.
