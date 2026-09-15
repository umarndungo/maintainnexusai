# MaintainNexus - Predictive Maintenance & Work Order Dispatch Infrastructure

<<<<<<< HEAD
MaintainNexus is a predictive maintenance and work order dispatch system designed to streamline industrial equipment maintenance workflows. It provides a complete pipeline from alert ingestion through technician dispatch, with automated scheduling, audit logging, inventory checks, and a Next.js dashboard UI (migration from the existing Flutter implementation).
=======
> Phase 2 web dashboard: use `web/` (Next.js). The mobile target is `technician-mobile-app/`
> (Flutter) — `maintain_nexus_ui/`, the older Flutter dashboard, is disabled and renamed to
> `_disabled_maintain_nexus_ui/`. Use `docs/04-DEPLOYMENT-GUIDE.md` for current web deployment.
> Never replace the team guides in `docs/` with web build output.

## Run the current Next.js dashboard

```powershell
docker compose up --build
```

This includes the web container at http://localhost:3000 and the backend at http://localhost:8000/docs. For frontend development against a local or shared API, see `web/README.md`. The current backend demo user IDs are `engineer-demo`, `supervisor-demo`, and `executive-demo`.

Current contract gaps are recorded in `docs/FRONTEND-INTEGRATION-STATUS.md`; a passing frontend build does not establish completion of every backend/ML/mobile requirement.


MaintainNexus is a predictive maintenance and work order dispatch system designed to streamline industrial equipment maintenance workflows. It provides a complete pipeline from alert ingestion through technician dispatch, with automated scheduling, audit logging, inventory checks, and a Flutter dashboard UI.
>>>>>>> 71e2efe2d68cd43dd44afd7755372df259c9948e

## Architecture Overview

The codebase is organized into modular domains for parallel development:

```
maintain-nexus/
├── api/             # Mock FastAPI service suite (Inventory, Alerts, HR, Work Orders, Dashboard)
├── etl/             # Data pipeline: extraction, validation, transformation, loading
├── database/        # PostgreSQL persistence with SQLAlchemy ORM and audit logging
<<<<<<< HEAD
├── maintain_nexus_ui/ # Legacy Flutter UI retained during migration to Next.js
├── frontend/         # Next.js dashboard target (to be created)
=======
├── _disabled_maintain_nexus_ui/ # Old Flutter dashboard, disabled — see technician-mobile-app/
>>>>>>> 71e2efe2d68cd43dd44afd7755372df259c9948e
├── tests/           # Pytest integration and unit tests
└── .github/         # CI/CD automation via GitHub Actions
```

## Prerequisites

- Docker and Docker Compose installed
  - Install from: https://docs.docker.com/get-docker/
- Flutter SDK installed and configured
  - Install from: https://docs.flutter.dev/get-started/install
  - Verify with:
    ```bash
    flutter doctor
    ```
- A supported Flutter desktop target if you want to run on Linux, macOS, or Windows
  - Enable desktop support:
    ```bash
    flutter config --enable-linux-desktop
    flutter config --enable-macos-desktop
    flutter config --enable-windows-desktop
    ```

## Backend Quickstart

1. **Clone the repository:**
   ```bash
   git clone https://github.com/org/maintain-nexus.git
   cd maintain-nexus
   ```

2. **Create the local environment file:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` to set the host ports, public API/domain address, database credentials, `AUTH_SECRET`,
   and `INTERNAL_SERVICE_TOKEN`. `.env` is ignored by Git and must never be committed. Compose uses
   `API_BASE_URL` for host/public clients and `API_INTERNAL_BASE_URL` with Docker service names
   (`web_api`, `postgres_db`, and `redis`) for container-to-container traffic. Host clients use the
   published `API_PORT`.

3. **Launch backend services with Docker Compose:**
   ```bash
   make up
   ```

   `make up` runs `scripts/setup_db.sh` (fills in any blank required secret —
   `POSTGRES_PASSWORD`, `APP_DB_PASSWORD`, `AUTH_SECRET`, `INTERNAL_SERVICE_TOKEN` — starts
   `postgres_db`/`redis`, waits for Postgres to report healthy, and runs `db_migrations`), then
   brings up the rest of the stack. Equivalent to running `./scripts/setup_db.sh` followed by
   `docker compose up -d --build`; use the plain `docker compose up --build` form directly if you'd
   rather manage `.env` and migrations yourself.

   Compose starts:
   - `web_api`: FastAPI at `http://localhost:8000`
   - `postgres_db`: PostgreSQL on port `5432`
   - `redis`: Celery broker/backend on port `6379`
   - `db_migrations`: one-shot admin migration and grant job
   - `celery_worker`: asynchronous alert, ML scoring, and work-order processing
   - `celery_beat`: five-minute demo telemetry and stale-approval escalation schedules

   `db_migrations` connects as `POSTGRES_USER` and creates the schema, the `maintain_app` runtime
   role, additive legacy columns, and database grants. The API, worker, and beat connect using
   `APP_DB_USER` and cannot update or delete rows in `audit_logs` or
   `work_order_lifecycle_events`. Runtime services wait for the migration job to complete before
   starting.

4. **Open API docs:**
   Visit `http://localhost:${API_PORT}/docs`, using the `API_PORT` value from `.env`.

5. **Get a development bearer token:**
   ```bash
   TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
     -H 'Content-Type: application/json' \
     -d '{"user_id":"engineer-demo"}' | python -c \
     'import json,sys; print(json.load(sys.stdin)["access_token"])')
   ```

   The available development users are `tech-demo`, `engineer-demo`, `executive-demo`, and
   `supervisor-demo`. Production authentication must replace these demo users and set a strong
   `AUTH_SECRET`.

6. **Check the authenticated API:**
   ```bash
   curl http://localhost:8000/api/v1/auth/me \
     -H "Authorization: Bearer $TOKEN"
   curl http://localhost:8000/api/v1/dashboard/summary \
     -H "Authorization: Bearer $TOKEN"
   ```

7. **Submit telemetry:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/alerts/telemetry \
     -H "Authorization: Bearer $TOKEN" \
     -H 'Content-Type: application/json' \
     -d '{"equipment_id":"PUMP-101","temperature":90,"vibration":2,"installation_age_hours":1000,"timestamp":"2026-09-13T12:00:00Z"}'
   ```

   Telemetry returns `202` after validation and queueing. ML scoring occurs in `celery_worker`, not
   inside the Uvicorn request handler. Watch the asynchronous path with:
   ```bash
   docker compose logs -f web_api celery_worker celery_beat
   ```

8. **Stop the backend:**
   ```bash
   make down
   ```

   To run the migration/grant job again after changing schema code:
   ```bash
   make migrate
   ```

   This job is idempotent. It does not delete historical rows or drop the legacy
   `work_orders.status` column.

9. **Run the mobile app** (`technician-mobile-app/` — see its README for details):
   ```bash
   cd technician-mobile-app
   flutter pub get
   flutter run
   ```

## Run the app

Backend + web dashboard:
```bash
make up
```
API docs at `http://localhost:8000/docs`, web dashboard at `http://localhost:3000` (see "Run the
current Next.js dashboard" above).

**`maintain_nexus_ui/` (the old Flutter dashboard) is disabled** — renamed to
`_disabled_maintain_nexus_ui/`, no longer part of the standard run/build/deploy workflow. The
maintained mobile client is `technician-mobile-app/` (see `technician-mobile-app/README.md` for
`flutter run`/`flutter build` instructions there instead).

## Feature Summary

- **Alert ingestion** via `/api/v1/alerts/maintenance` with asynchronous Celery task processing
- **Technician lookup** via `/api/v1/hr/technicians/available`
- **Inventory checks** via `/api/v1/warehouse/stock`
- **Work order dispatch** via `/api/v1/maintenance/work-orders`
- **Work order status** is derived exclusively from append-only lifecycle events
- **Alert/work order correlation** via `alert_task_id`, preserving the originating alert ID on the dispatched work order
- **Dashboard summary** via `/api/v1/dashboard/summary`
- **Schema migrations** run in the one-shot `db_migrations` service before any backend service starts — it creates the schema, additive columns like `alert_task_id` for existing databases, and the least-privilege `maintain_app` role
- **Backend health status** now exposes `backend_status` in the dashboard summary response for clearer frontend state and diagnostics
- **Unique scheduled alerts** are generated each Celery run to prevent repeated duplicate mock ingestion
- **Duplicate-safe APIs** dedupe work orders and recent alerts before returning lists
- **Flutter UI** with live counts, technician availability, inventory status, and navigation to recent orders and alerts
- **Backend refresh behavior** handles eventual consistency for async alert ingestion by polling the summary endpoint after task submission
- **Phase 2 security** requires signed bearer tokens and server-side role checks on every API router
- **Internal services** use `X-Internal-Service`; `/api/v1/notifications/sms` is never available to end-user roles
- **Downtime** is persisted as equipment windows opened at dispatch and closed at completion
- **Live events** are available through the authenticated `/api/v1/events` SSE feed
- **ML risk scoring** is available through the internal `/api/v1/ml/predict-risk` endpoint; live ETL calls it with `X-Internal-Service`
- **Telemetry ingestion** returns `202` after validation and queueing; the Celery worker performs ML scoring asynchronously

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/warehouse/stock` | Check part inventory availability |
| POST | `/api/v1/alerts/maintenance` | Ingest maintenance alert from equipment |
| GET | `/api/v1/hr/technicians/available` | Find available technicians by certification |
| POST | `/api/v1/maintenance/work-orders` | Dispatch a work order to a technician |
| GET | `/api/v1/dashboard/summary` | Retrieve dashboard summary counts, available technicians, and inventory status |
| POST | `/api/v1/alerts/telemetry` | Ingest raw telemetry and create an alert payload when the risk threshold is exceeded |
| POST | `/api/v1/auth/login` | Issue a one-hour signed bearer token for a demo user |
| GET | `/api/v1/auth/me` | Return the authenticated user and role/station claims |
| PATCH | `/api/v1/maintenance/work-orders/{id}/approve` | Engineer/supervisor approval transition |
| PATCH | `/api/v1/maintenance/work-orders/{id}/reject` | Engineer/supervisor rejection transition |
| PATCH | `/api/v1/maintenance/work-orders/{id}/escalate` | Supervisor/internal SLA escalation transition |
| GET | `/api/v1/maintenance/work-orders/{id}/lifecycle` | Read persisted lifecycle history |
| GET | `/api/v1/dashboard/equipment/{id}/downtime` | Read equipment downtime windows |
| GET | `/api/v1/dashboard/executive-summary` | Read executive downtime aggregation |
| GET | `/api/v1/events` | Authenticated server-sent events stream |
| POST | `/api/v1/notifications/sms` | Internal-only notification queue boundary |
| POST | `/api/v1/ml/predict-risk` | Internal-only XGBoost risk scoring contract |

## Dashboard Summary Endpoint

The new dashboard endpoint aggregates key app state into a single response:

- `work_order_count`
- `alert_count`
- `available_technicians`
- `inventory`

The Flutter dashboard consumes this endpoint to keep the UI in sync with backend state.

## Flutter Dashboard UI

`_disabled_maintain_nexus_ui/` (the old Flutter dashboard this section described) is disabled. The
web dashboard is `web/` (Next.js); the maintained mobile client is `technician-mobile-app/`.

## ETL Pipeline Flow

1. **Ingest** — Raw telemetry is accepted and validated before any scoring or alert construction
2. **Validate** — Telemetry payload is checked for required fields, timestamp sanity, and numeric sensor values
3. **Score** — Valid telemetry is scored and converted into a model-driven alert payload when risk exceeds threshold
4. **Extract Stock** — Part inventory is checked via the warehouse API
5. **Extract Technician** — Available certified technician is fetched from HR
6. **Transform** — Alert + technician data is combined into a work order payload
7. **Load** — Work order is dispatched via the work orders API

## Database Schema

- **work_orders** — Tracks dispatched work orders with equipment, technician, part, status, timestamps, and optional `alert_task_id` linking to the source alert
- **work_order_lifecycle_events** — Hash-chained, insert-only lifecycle transitions; current status is read from the latest event
- **downtime_windows** — Equipment downtime intervals linked to work orders
- **audit_logs** — Hash-chained append-only operational audit events
- **audit_logs** — Records all pipeline events with event name, payload, and timestamp

## Work Order Lifecycle

```text
CREATED → PARTS_RESERVED → DISPATCHED
```

## Scheduler

A periodic scheduler runs a sample pipeline every 5 minutes to simulate automated alert handling and work order creation. Each scheduled run now generates a unique sample alert payload so repeated jobs do not enqueue the same static alert data.

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v
```

`tests/test_db_migrations_grants.py` is a Postgres integration test proving that the `maintain_app`
role is rejected by the database itself on `UPDATE`/`DELETE` against `audit_logs` and
`work_order_lifecycle_events`. It skips automatically when no Postgres is reachable. To run it for
real, point `TEST_ADMIN_DATABASE_URL` at an admin connection (e.g. the Compose `postgres_db` service
published to the host) before running `pytest`.

## Release Notes

### Database setup helper script

- Added `scripts/setup_db.sh`, a wrapper around `docker-compose.yml` for first-time local setup: it
  creates `.env` from `.env.example` if missing, generates a random value for any of
  `POSTGRES_PASSWORD` / `APP_DB_PASSWORD` / `AUTH_SECRET` / `INTERNAL_SERVICE_TOKEN` left blank,
  brings up `postgres_db` and `redis`, waits for Postgres to report healthy, and runs `db_migrations`.
  It does not add any database logic of its own — `database/run_migrations.py` remains the one place
  that creates the schema, the `maintain_app` role, and its grants.
- Added a `Makefile` (`up`, `down`, `migrate`, `logs`, `ps`) so `make up` runs the setup script and
  then starts the full stack in one command; `make down`/`make migrate` wrap the corresponding
  `docker compose` calls.

### Database migration service and least-privilege application role

- Added a one-shot `db_migrations` Compose service that runs schema creation, additive column
  migrations, and database grants as the PostgreSQL admin role, before any other service starts.
- Added a dedicated `maintain_app` runtime role: full CRUD on operational tables, but only
  `SELECT`/`INSERT` on `audit_logs` and `work_order_lifecycle_events` — `UPDATE`/`DELETE` on those
  two tables is revoked at the database grant level. `web_api`, `celery_worker`, and `celery_beat`
  now connect as `maintain_app` instead of the PostgreSQL admin role.
- Removed the old startup schema initialization (`database/init_db.py`) from the API lifespan and
  the Celery worker-ready signal, now that `db_migrations` runs before those services start.
- Added `tests/test_db_migrations_grants.py` to prove the grant revocation against a real Postgres
  database rather than by inspection of the migration SQL alone.

### Backend schema and alert-work order correlation

- Added `alert_task_id` to the `work_orders` schema so every dispatched work order can be correlated back to its originating alert.
- Updated startup initialization to auto-migrate existing Postgres databases by adding the missing `alert_task_id` column when needed.
- Preserved Celery startup retry behavior with `broker_connection_retry_on_startup=True`, avoiding warning noise in newer Celery versions.

## Tech Stack

- **FastAPI** — API framework
- **SQLAlchemy** — ORM for PostgreSQL
- **Celery** — Async task queue for alert processing
- **Pydantic** — Data validation
- **Pytest** — Testing
- **Docker Compose** — Container orchestration
- **Flutter** — Dashboard UI

## Deploying

`maintain_nexus_ui/` (the old Flutter web dashboard this section covered — Netlify/GitHub Pages
static hosting) is disabled; that guidance no longer applies. Current deployment docs:

<<<<<<< HEAD
### Build the web app

```bash
cd maintain_nexus_ui
flutter pub get
flutter build web --release
```

The built static files will be available in `maintain_nexus_ui/build/web/`.

### Deploy to Netlify

1. Build the app as shown above.
2. In the Netlify dashboard, drag and drop the `maintain_nexus_ui/build/web/` folder.
3. Or use the Netlify CLI:

```bash
npm install -g netlify-cli
cd maintain_nexus_ui
netlify deploy --dir=build/web
netlify deploy --dir=build/web --prod
```

> If your dashboard uses client-side routing later, add a `_redirects` file in `build/web/` with:
>
> ```text
> /* /index.html 200
> ```

### Deploy to GitHub Pages

#### Option A: Use the `docs/` folder

```bash
cd maintain_nexus_ui
flutter build web --release
rm -rf ../docs
mkdir ../docs
cp -r build/web/* ../docs/
cd ..
git add docs
git commit -m "Deploy Flutter web dashboard to GitHub Pages"
git push
```

Then enable GitHub Pages in repository settings:
- Source: `main` branch
- Folder: `/docs`

#### Option B: Use `gh-pages` branch

1. Build the app:

```bash
cd maintain_nexus_ui
flutter build web --release
```

2. Push the contents of `build/web/` to a `gh-pages` branch using a deploy script or GitHub Action.
3. Enable GitHub Pages from the `gh-pages` branch.

### Important note

The hosted frontend is static only. The backend must remain available independently, so update the dashboard API base URL to point to the hosted FastAPI backend rather than `localhost`.

### Backend hosting guidance

The backend should be deployed as a separate service, such as:

- **Railway**, **Render**, **Fly.io**, or **Heroku** for the FastAPI app
- **Docker Compose** locally for development
- **PostgreSQL** and **Redis** must also be hosted or managed for production

Common backend hosting setup:

1. Deploy the FastAPI app and expose the API at a public base URL.
2. Ensure the Celery worker is running with access to Redis.
3. Point the Flutter web app configuration at the public API URL.

If the backend is served at `https://api.example.com`, the frontend should use that URL for all API calls.

### Example frontend configuration

The Flutter app reads its backend base URL from a compile-time environment variable.

Build the web app with a hosted backend URL like this:

```bash
cd maintain_nexus_ui
flutter build web --release --dart-define=API_BASE_URL=https://api.example.com/api/v1
```

For local development, the app still defaults to:

```dart
http://localhost:8000/api/v1
```

If the backend is deployed to a different hostname or path, change `API_BASE_URL` accordingly.


## Target operational workflow

`Telemetry → ML prediction → decision engine → automated API action → operational outcome → feedback`

The platform covers **pumps, loading arms and valves**. Automated scheduling/reassignment is the prototype action target; safety-critical physical control is outside the ML service boundary.

Shared contracts: `docs/09-DATA-REQUIREMENTS-MATRIX.md`, `docs/10-ML-BACKEND-CONTRACT.md`, and `schemas/`.

**Data provenance:** public KPC information is used for verified context; raw KPC SCADA/IoT/CMMS data is not assumed public. Prototype data must be labelled synthetic.
=======
- **Backend** (FastAPI + Celery worker + Celery Beat): `render.yaml` at the repo root, or see
  `docs/04-DEPLOYMENT-GUIDE.md`.
- **Web dashboard** (`web/`, Next.js): `web/README.md`.
- **Mobile** (`technician-mobile-app/`, Flutter): `technician-mobile-app/README.md`.
>>>>>>> 71e2efe2d68cd43dd44afd7755372df259c9948e
