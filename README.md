# MaintainNexus - Predictive Maintenance & Work Order Dispatch Infrastructure

> Phase 2 web dashboard: use `web/` (Next.js). Flutter remains the mobile target. The Flutter web/static-hosting sections below describe the legacy target; use `docs/04-DEPLOYMENT-GUIDE.md` for current web deployment. Never replace the team guides in `docs/` with web build output.

## Run the current Next.js dashboard

```powershell
docker compose up --build
```

This includes the web container at http://localhost:3000 and the backend at http://localhost:8000/docs. For frontend development against a local or shared API, see `web/README.md`. The current backend demo user IDs are `engineer-demo`, `supervisor-demo`, and `executive-demo`.

Current contract gaps are recorded in `docs/FRONTEND-INTEGRATION-STATUS.md`; a passing frontend build does not establish completion of every backend/ML/mobile requirement.


MaintainNexus is a predictive maintenance and work order dispatch system designed to streamline industrial equipment maintenance workflows. It provides a complete pipeline from alert ingestion through technician dispatch, with automated scheduling, audit logging, inventory checks, and a Flutter dashboard UI.

## Architecture Overview

The codebase is organized into modular domains for parallel development:

```
maintain-nexus/
├── api/             # Mock FastAPI service suite (Inventory, Alerts, HR, Work Orders, Dashboard)
├── etl/             # Data pipeline: extraction, validation, transformation, loading
├── database/        # PostgreSQL persistence with SQLAlchemy ORM and audit logging
├── maintain_nexus_ui/ # Flutter dashboard application
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

## Quickstart Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/org/maintain-nexus.git
   cd maintain-nexus
   ```

2. **Launch backend services with Docker Compose:**
   ```bash
   docker compose up --build
   ```

   The backend will auto-create missing tables and apply a safe `alert_task_id` schema migration on first startup.

3. **Open API docs:**
   Visit [http://localhost:8000/docs](http://localhost:8000/docs).

4. **Run the Flutter dashboard:**
   ```bash
   cd maintain_nexus_ui
   flutter pub get
   flutter run
   ```
## Run the app

### Option A: Run locally with Docker Compose

1. Start the backend and required services:
   ```bash
   docker compose up --build
   ```
2. Confirm the API is available at:
   - `http://localhost:8000/docs`
3. In a second terminal, run the Flutter UI from the project root:
   ```bash
   cd maintain_nexus_ui
   flutter pub get
   flutter run
   ```
4. Open the Flutter app on the device/emulator shown by `flutter run`.

### Option B: Run the Flutter app directly

1. From the Flutter app directory:
   ```bash
   cd maintain_nexus_ui
   flutter pub get
   flutter run
   ```
2. The app assumes the backend API is available at `http://localhost:8000/api/v1` by default.

### Run the Flutter app on web

1. Build for web:
   ```bash
   cd maintain_nexus_ui
   flutter build web --release
   ```
2. Serve locally for testing:
   ```bash
   cd maintain_nexus_ui/build/web
   python3 -m http.server 8080
   ```
3. Open `http://localhost:8080` in your browser.

### Run the Flutter app on desktop

1. Ensure desktop support is enabled:
   ```bash
   flutter config --enable-linux-desktop
   flutter config --enable-macos-desktop
   flutter config --enable-windows-desktop
   flutter doctor
   ```
2. Run on the desktop target:
   ```bash
   cd maintain_nexus_ui
   flutter run -d linux
   ```

> Replace `linux` with `macos` or `windows` as needed.

## Feature Summary

- **Alert ingestion** via `/api/v1/alerts/maintenance` with asynchronous Celery task processing
- **Technician lookup** via `/api/v1/hr/technicians/available`
- **Inventory checks** via `/api/v1/warehouse/stock`
- **Work order dispatch** via `/api/v1/maintenance/work-orders`
- **Work order status** is derived exclusively from append-only lifecycle events
- **Alert/work order correlation** via `alert_task_id`, preserving the originating alert ID on the dispatched work order
- **Dashboard summary** via `/api/v1/dashboard/summary`
- **Startup schema migration** automatically adds the `alert_task_id` column for existing PostgreSQL databases on first backend startup
- **Backend health status** now exposes `backend_status` in the dashboard summary response for clearer frontend state and diagnostics
- **Unique scheduled alerts** are generated each Celery run to prevent repeated duplicate mock ingestion
- **Duplicate-safe APIs** dedupe work orders and recent alerts before returning lists
- **Flutter UI** with live counts, technician availability, inventory status, and navigation to recent orders and alerts
- **Backend refresh behavior** handles eventual consistency for async alert ingestion by polling the summary endpoint after task submission
- **Phase 2 security** requires signed bearer tokens and server-side role checks on every API router
- **Internal services** use `X-Internal-Service`; `/api/v1/notifications/sms` is never available to end-user roles
- **Downtime** is persisted as equipment windows opened at dispatch and closed at completion
- **Live events** are available through the authenticated `/api/v1/events` SSE feed
- **ML service integration** is intentionally deferred; the live ETL path must not be documented as calling `/api/v1/ml/predict-risk` until that service contract exists

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

## Dashboard Summary Endpoint

The new dashboard endpoint aggregates key app state into a single response:

- `work_order_count`
- `alert_count`
- `available_technicians`
- `inventory`

The Flutter dashboard consumes this endpoint to keep the UI in sync with backend state.

## Flutter Dashboard UI

The dashboard now includes:

- top-level system status and refresh indicator
- quick actions for sample work order dispatch and sample alert submission
- available technician list and current inventory status cards
- navigation cards for recent work orders and recent alerts
- a scrollable layout with pull-to-refresh support

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

## Release Notes

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

## Deploying the Flutter Dashboard

This project includes a web-ready Flutter dashboard at `maintain_nexus_ui/`.

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
mkdir -p ../legacy-web-site
cp -r build/web/* ../legacy-web-site/
cd ..
git add legacy-web-site
git commit -m "Deploy Flutter web dashboard to GitHub Pages"
git push
```

Then enable GitHub Pages in repository settings:
- Source: `main` branch
- Folder: use a separate publishing branch or hosting provider; keep `/docs` for team guides.

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
