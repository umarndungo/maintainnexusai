"""
Prometheus Metrics — Pipeline Performance Monitoring.

Exposes counters and histograms so operators can track:
- How many pipelines succeeded / failed.
- How long each pipeline phase takes.
- Current stock-out / no-tech-available events.

These are served at ``GET /metrics`` by the FastAPI app.
"""

from prometheus_client import Counter, Histogram, CollectorRegistry

# A custom registry so we don't conflict with any global default.
REGISTRY = CollectorRegistry()

# ---- Pipeline outcomes ----------------------------------------------------
pipeline_results = Counter(
    "pipeline_results_total",
    "ETL pipeline final outcome (success / failure / hold)",
    labelnames=["status"],
    registry=REGISTRY,
)

# ---- Pipeline duration (wall-clock time in seconds) -----------------------
pipeline_duration = Histogram(
    "pipeline_duration_seconds",
    "Time spent executing a full pipeline run",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")),
    registry=REGISTRY,
)

# ---- Per-phase breakdown --------------------------------------------------
phase_duration = Histogram(
    "pipeline_phase_duration_seconds",
    "Time spent in each ETL phase",
    labelnames=["phase"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float("inf")),
    registry=REGISTRY,
)

# ---- Business-logic events ------------------------------------------------
stock_out_events = Counter(
    "stock_out_events_total",
    "Number of times a requested part was unavailable",
    labelnames=["part_number"],
    registry=REGISTRY,
)

no_technician_events = Counter(
    "no_technician_events_total",
    "Number of times no certified technician was available",
    registry=REGISTRY,
)

alerts_ingested = Counter(
    "alerts_ingested_total",
    "Total maintenance alerts received by the gateway",
    registry=REGISTRY,
)
