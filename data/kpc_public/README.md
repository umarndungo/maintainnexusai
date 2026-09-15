# KPC public equipment inventory (Layer 1)

This folder is **real public KPC evidence**: equipment types, models, stations, components, and procurement context.

It is **not** KPC telemetry, work orders, or failure labels. Those fields are `INTERNAL` or `SYNTHETIC` — see `docs/09-DATA-REQUIREMENTS-MATRIX.md` and `docs/11-PRODUCT-CONTRACT.md`.

| File | Contents |
|---|---|
| `sources.csv` | Citation for every row we extracted |
| `assets.csv` | Pumps, valves, loading-related assets we can name from public docs |
| `spare_parts.csv` | Spare/component list from tenders |
| `failure_modes.csv` | Failure modes inferred from those components (engineering mapping, not KPC incident logs) |
| `availability.csv` | What is public vs internal vs synthetic for the MVP model |

Do not describe this data as “KPC sensor data.”
