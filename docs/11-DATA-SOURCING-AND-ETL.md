# Data Sourcing → Synthetic Data → ETL

## Purpose

This phase establishes the reproducible data foundation before final ML model development.

### Provenance rule

- `KPC_PUBLIC`: publicly documented KPC context, specifications, reports and procurement evidence.
- `EXTERNAL_PUBLIC`: public industrial/predictive-maintenance datasets used for benchmarking or feature-method development.
- `SYNTHETIC`: generated prototype data representing KPC-style operational structures; never described as actual KPC telemetry.
- `INTERNAL`: future SCADA/IoT/SAP/CMMS/operations data requiring authorized access.

## Public sources selected

1. UCI AI4I 2020 — baseline industrial failure classification. It is itself synthetic and should not be treated as real KPC data.
2. UCI Condition Monitoring of Hydraulic Systems — especially relevant because it contains pressure, flow, temperature and vibration measurements and labelled pump/valve conditions.
3. CWRU Bearing Data Center — vibration data for normal and seeded bearing faults; useful for rotating-equipment vibration feature engineering.
4. KPC annual reports — context/provenance only; not raw telemetry.

## Download

Run:

```bash
python scripts/download_public_data.py --source uci_ai4i_2020
python scripts/download_public_data.py --source uci_hydraulic_447
```

The raw files remain outside Git history through `.gitignore`.

## Synthetic operational data

Run:

```bash
python scripts/generate_synthetic_operational_data.py
```

This creates equipment, telemetry, failures, maintenance, loading points, truck schedules and spare-parts data for the prototype.

## ETL

Run:

```bash
python scripts/run_ml_etl.py
```

The ETL produces the canonical ML dataset under `data/processed/`.

## Important limitation

The external benchmark datasets are not substitutes for KPC SCADA/SAP/CMMS data. The production model must be recalibrated/validated against authorized operational data before operational deployment.

## Public benchmark ingestion (added)

Once the source ZIPs exist under `data/raw/`, run:

```bash
python scripts/run_public_etl.py --source all
```

This creates separate benchmark outputs under `data/processed/public_benchmarks/`:

- `uci_ai4i_2020_normalized.csv`
- `uci_hydraulic_447_cycle_features.csv`

The public ETL deliberately does **not** append these rows to the KPC-style synthetic canonical dataset. Their targets have different semantics and must remain separately evaluated.

### Expected handoff

- ML: uses the benchmark outputs for feature engineering/model benchmarking.
- Data/ETL: owns extraction and provenance.
- Backend: should consume only the agreed production prediction contract, not raw benchmark tables.
- Team lead: receives the provenance/limitations documented in `docs/12-PUBLIC-DATA-INGESTION-MAPPING.md`.
