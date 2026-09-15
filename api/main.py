"""
MaintainNexus API — Application Entry Point.

Aggregates all domain routers (Equipment, Alerts, HR, Work Orders) into a
single FastAPI application so the whole service can be served by Uvicorn.

Includes:
- ``GET  /``          — API metadata (health-check).
- ``GET  /metrics``   — Prometheus metrics (pipeline counts, latency).
- ``Lifespan``        — ensures DB tables exist on startup / shutdown.
"""

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from api.dashboard import router as dashboard_router
from api.events import router as events_router
from api.hse import router as hse_router
from api.auth import router as auth_router
from api.equipment import router as equipment_router
from api.maintenance import router as maintenance_router
from api.ml import router as ml_router
from api.monitoring import router as monitoring_router
from api.monitoring import internal_router as monitoring_internal_router
from api.notifications import router as notifications_router
from api.notifications import public_router as notifications_public_router
from api.auth import get_current_user
from api.technicians import router as technicians_router
from api.workorders import router as workorders_router

from etl.metrics import REGISTRY, pipeline_duration, pipeline_results


# ---------------------------------------------------------------------------
# Application lifespan — runs on startup & shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run the API after the external migration service has prepared the schema."""
    yield


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MaintainNexus API",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local development and Flutter Web clients.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root(request: Request, _user: dict = Depends(get_current_user)) -> JSONResponse:
    """
    Landing page — returns API metadata and links to available routes.
    """
    base_url = str(request.base_url).rstrip("/")
    return JSONResponse(
        {
            "service": app.title,
            "version": app.version,
            "docs": f"{base_url}/docs",
            "openapi": f"{base_url}/openapi.json",
            "endpoints": {
                "inventory": "/api/v1/warehouse/stock?part_number=...",
                "technicians": "/api/v1/hr/technicians/available?required_cert=...",
                "dashboard_summary": "/api/v1/dashboard/summary",
                "alerts": "/api/v1/alerts/maintenance (POST)",
                "work_orders": "/api/v1/maintenance/work-orders (POST)",
                "metrics": "/metrics",
            },
        }
    )


@app.get("/metrics", include_in_schema=False)
async def metrics(_user: dict = Depends(get_current_user)) -> Response:
    """
    Prometheus metrics endpoint — exposes pipeline performance counters.

    Metrics
    -------
    - pipeline_duration_seconds  : histogram of pipeline run duration.
    - pipeline_results_total     : counter of success / failure outcomes.
    """
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )


# ---------------------------------------------------------------------------
# Domain routers
# ---------------------------------------------------------------------------
app.include_router(dashboard_router)
app.include_router(auth_router)
app.include_router(events_router)
app.include_router(hse_router)
app.include_router(equipment_router)
app.include_router(maintenance_router)
app.include_router(ml_router)
app.include_router(monitoring_router)
app.include_router(monitoring_internal_router)
app.include_router(notifications_router)
app.include_router(notifications_public_router)
app.include_router(technicians_router)
app.include_router(workorders_router)
