# MaintainNexus Next.js frontend

## Start locally

Use Node.js 22 or newer. From the repository root:

```powershell
cd web
npm.cmd ci
Copy-Item .env.example .env.local
npm.cmd run dev
```

Open http://localhost:3000/login. The current backend accepts a demo `user_id`: `engineer-demo`, `supervisor-demo`, or `executive-demo`. Role selection prefills this ID; `/auth/me` determines the actual workspace. This is backend demo authentication, not offline/mock mode or production password authentication.

In a second terminal, start the backend services from the repository root:

```powershell
docker compose up --build postgres_db redis web_api celery_worker celery_beat
```

Alternatively, `docker compose up --build` includes the frontend container at port 3000; do not also start `npm run dev` on that port.

## Use a shared backend

Set `API_BASE_URL=https://your-api-host` in `web/.env.local` and restart Next.js. Use the API origin without `/api/v1`. All browser calls go through the Next.js server, including login, actions, and SSE; no browser bearer token or `NEXT_PUBLIC_API_BASE_URL` is needed. A teammate can run only the frontend when a compatible shared backend is reachable.

## Views and connections

- Engineers: summaries, equipment health, recent alerts, filtered work orders, approval/rejection, lifecycle drawer/detail, equipment downtime/history, audit records.
- Supervisors: the engineer shell plus escalation queue and manual escalation; executive rollup access.
- Executives: read-only impact and audit pages. No engineer queue or mutation access.
- Technicians: redirected away from the web dashboard to use mobile.

Every protected page validates `/api/v1/auth/me`. Expired tokens require sign-in; unavailable identity validation blocks protected data. JWTs remain in an httpOnly cookie with the current backend's one-hour expiry. Live updates use authenticated SSE `/api/v1/events` through `/api/events`; native reconnection reloads data after reconnect. There is no polling loop.

The existing telemetry/work-order/HSE demo controls remain. HSE is a preserved optional extension using simulated tank snapshots, not live KPC sensors or physical equipment control.

## Checks

```powershell
npm.cmd run lint
npm.cmd run build
npm.cmd run typecheck
npm.cmd run test:smoke
```

Smoke checks start a production Next.js server against a test-only mock API and cover session validation, redirects, cookie authentication, forbidden roles, filters, SSE proxying, and current/planned executive response shapes. They require a completed build. These mocks never run in the app.

## Backend handoff

See `../docs/FRONTEND-INTEGRATION-STATUS.md` for the connection matrix and missing backend fields. Missing APIs remain connected and display unavailable states. The frontend does not manufacture savings, verification, risk explanations, or model features.
