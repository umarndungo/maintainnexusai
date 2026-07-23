# MaintainNexus Tutorial

This tutorial explains how to create, run, and deploy the MaintainNexus project. It is written for a beginner and includes the full workflow, the project structure, the backend/frontend setup, and deployment guidance.

## Project Overview

MaintainNexus is a predictive maintenance and work order dispatch system. It has two main parts:

- **Backend**: A Python service built with FastAPI, Celery, SQLAlchemy, and a local database.
- **Frontend**: A Flutter dashboard app inside `maintain_nexus_ui/`.

The app supports:
- alert ingestion through an async pipeline
- technician lookup
- inventory checks
- work order dispatch
- computed work order lifecycle status and elapsed duration
- deduped work order and alert listing APIs
- a dashboard summary endpoint
- a Flutter dashboard UI with counts, technician availability, inventory status, and recent work orders/alerts

## Project Structure

At the repository root, the main folders are:

- `api/` - FastAPI routes for alerts, work orders, equipment, technicians, and dashboard summary
- `database/` - database connection, models, and initialization logic
- `etl/` - extract-transform-load pipeline modules for alert processing
- `maintain_nexus_ui/` - Flutter dashboard application
- `tests/` - Python test files
- `scripts/` - helper scripts such as `reset_and_seed_data.py`

## Prerequisites

You need these installed locally:

- Python 3
- Flutter SDK
- Docker and Docker Compose
- Node.js / npm (for Netlify CLI if you use Netlify)

## Setting Up the Project

1. Clone the repository:

```bash
git clone https://github.com/org/maintain-nexus.git
cd maintain-nexus
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Install Flutter dependencies for the UI:

```bash
cd maintain_nexus_ui
flutter pub get
cd ..
```

## Running the Backend Locally

The backend is designed to run with Docker Compose so the API, Celery worker, Redis, and database can work together.

1. Start the services:

```bash
docker compose up --build
```

2. Open the backend docs in your browser:

```text
http://localhost:8000/docs
```

## Running the Flutter Dashboard

1. Open the Flutter app folder:

```bash
cd maintain_nexus_ui
```

2. Run the Flutter app:

```bash
flutter run
```

The Flutter app is configured to call the backend at `http://localhost:8000/api/v1` by default.

## Working on the Project

When I worked on this project, I followed these steps:

1. **Inspect current code**: I read the existing files to understand how the backend and frontend were structured.
2. **Add new backend support**: I implemented `/api/v1/dashboard/summary` in `api/dashboard.py` so the UI could request a single aggregated summary.
3. **Improve Flutter UI**: I cleaned up `maintain_nexus_ui/lib/screens/dashboard_screen.dart` to make it scrollable, add status cards, and show technician and inventory panels.
4. **Make backend URL configurable**: I added `maintain_nexus_ui/lib/config.dart` and changed `maintain_nexus_ui/lib/services/api_service.dart` to use `API_BASE_URL` at build time.
5. **Create reset data script**: I added `scripts/reset_and_seed_data.py` to clear database alerts and work orders and generate unique sample data.
7. **Prevent duplicates**: I added dedupe logic in `api/workorders.py`, `api/maintenance.py`, and `maintain_nexus_ui/lib/services/api_service.dart` so lists only return unique work orders and alerts.
8. **Add unique scheduled alerts**: I updated `tasks.py` so the scheduled Celery pipeline job generates a new randomized sample alert every run.
9. **Add status lifecycle**: I updated `api/workorders.py` so backend work order status can move from `DISPATCHED` to `PROCESSING` to `EXECUTED` based on `created_at` elapsed time.
10. **Update documentation**: I expanded `README.md` with deployment and hosting instructions and updated this tutorial file.

## Resetting the Database

If you need to clear sample alerts and work orders, run:

```bash
cd maintain_nexus
PYTHONPATH='.' python3 scripts/reset_and_seed_data.py
```

This script resets the current work order and alert tables and then generates new unique sample records.

## Deployment and Hosting

The Flutter dashboard can be deployed as a static web app. The backend needs to be hosted separately.

### Build the Flutter Web App

```bash
cd maintain_nexus_ui
flutter pub get
flutter build web --release
```

The files to publish are in `maintain_nexus_ui/build/web/`.

### Deploy to Netlify

1. Build the app as shown above.
2. Use drag-and-drop in the Netlify dashboard to upload `maintain_nexus_ui/build/web/`.
3. Or use the Netlify CLI:

```bash
npm install -g netlify-cli
cd maintain_nexus_ui
netlify deploy --dir=build/web
netlify deploy --dir=build/web --prod
```

If you use client-side routing later, add a `_redirects` file in `build/web/` with:

```text
/* /index.html 200
```

### Deploy to GitHub Pages

#### Option A: Use `docs/`

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

Then set GitHub Pages source to:
- branch: `main`
- folder: `/docs`

#### Option B: Use `gh-pages`

1. Build the app:

```bash
cd maintain_nexus_ui
flutter build web --release
```

2. Push `build/web/` content to a `gh-pages` branch.
3. Enable GitHub Pages from the `gh-pages` branch.

### Backend Hosting Guidance

The backend must run separately from the frontend. Common hosting options are:

- Railway
- Render
- Fly.io
- Heroku

You also need a hosted data store for PostgreSQL and Redis for Celery.

When the backend is hosted at a public URL, build the Flutter app with:

```bash
cd maintain_nexus_ui
flutter build web --release --dart-define=API_BASE_URL=https://api.example.com/api/v1
```

Replace `https://api.example.com/api/v1` with your actual hosted backend base URL.

## Beginner Tips

- Use `flutter analyze` to catch UI issues early.
- Read the backend routes in `api/` first to understand available APIs.
- Use `docker compose up --build` to start all backend services together.
- Keep the frontend and backend code separate while developing.
- When you change the Flutter config, rebuild the web app.

## Useful Commands

```bash
# Start backend
docker compose up --build

# Run Flutter app locally
cd maintain_nexus_ui
flutter run

# Analyze Flutter screen files
flutter analyze lib/screens/dashboard_screen.dart

# Reset backend sample data
cd maintain_nexus
PYTHONPATH='.' python3 scripts/reset_and_seed_data.py

# Build Flutter web for production
cd maintain_nexus_ui
flutter build web --release
```

## Final Notes

This project is a full-stack proof of concept for predictive maintenance.
The main learning path is:

1. understand the backend API routes,
2. inspect the Flutter app structure,
3. run the system locally,
4. add features in small incremental steps,
5. deploy the frontend as static files and host the backend separately.
