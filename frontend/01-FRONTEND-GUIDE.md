# Frontend Implementation Guide — Next.js Dashboard

**Owners:** Frontend track owner(s)
**Replaces:** Flutter Web target only. Flutter stays for mobile — see `08-MOBILE-GUIDE.md`.
**Reads:** `00-PROJECT-DOC.md` §4 (API contract) and §3 (roles) before starting.

---

## 1. Scope

Two role-gated views inside one Next.js app:

1. **Engineer view** — per-station technical dashboard: live telemetry health, pending approvals,
   risk-driver breakdown, station audit log.
2. **Executive view** — cross-station rollup: downtime avoided, cost saved, uptime trend. Read-only.
3. **Supervisor view** (shared shell with engineer view) — escalation queue.

## 2. Why Next.js here specifically

- Server components let you fetch role-scoped data server-side, so an engineer's browser never even
  receives another station's data — this matters because RBAC in the API is the real gate, but
  minimizing what reaches the client is good practice on top of it.
- Built-in API routes are fine for thin proxying (e.g. attaching the JWT), but **do not reimplement
  backend logic in a Next.js API route** — every real operation goes through the FastAPI contract in
  the project doc.
- Use SSE (`EventSource`) or a WebSocket client against `GET/WS /api/v1/events` for live updates —
  no polling loops. Confirm with backend which transport they're implementing before you build the
  client for it.

## 3. Exact API surface this app consumes

| Endpoint | Used for |
|---|---|
| `POST /api/v1/auth/login` | Login screen |
| `GET /api/v1/auth/me` | Role + station scoping on every page load |
| `GET /api/v1/alerts/recent` | Engineer view — live alert feed |
| `GET /api/v1/maintenance/work-orders` | Engineer view — list + filter by status |
| `PATCH /api/v1/maintenance/work-orders/{id}/approve` | Approve button |
| `PATCH /api/v1/maintenance/work-orders/{id}/reject` | Reject button |
| `PATCH /api/v1/maintenance/work-orders/{id}/escalate` | Supervisor manual escalate |
| `GET /api/v1/maintenance/work-orders/{id}/lifecycle` | Work order detail drawer |
| `GET /api/v1/dashboard/summary` | Home/overview cards |
| `GET /api/v1/dashboard/equipment/{id}/downtime` | Equipment detail page |
| `GET /api/v1/dashboard/executive-summary` | Executive view |
| `GET /api/v1/dashboard/audit-logs` | Audit log page |
| `GET /api/v1/dashboard/audit-logs/verify` | Audit log page — chain-integrity indicator |
| `GET/WS /api/v1/events` | Live updates on all of the above |

If any of these don't exist yet when you start, coordinate with backend rather than mocking a shape
you're guessing at — the risk-driver fields in particular (from `/predict-risk`, surfaced via the
work-order lifecycle) need to match exactly what the model actually returns.

## 4. Task breakdown

**Workstream A — auth, engineer view, live events**
- App shell: auth flow, role-based routing/middleware (redirect technician-only tokens away from
  dashboard entirely — belt-and-suspenders with server RBAC).
- Engineer view: pending-approvals list, approve/reject actions, risk-driver display component
  (this is the "why is this flagged" UI — take the top-N contributing features from the ML response
  and render them as a short readable list, not a raw JSON dump).
- Live event wiring (SSE/WebSocket client + reconnect handling).

**Workstream B — executive view, equipment/audit pages**
- Executive view: downtime-avoided and cost-saved cards, uptime trend chart, per-station comparison.
- Equipment detail page (downtime windows, service history).
- Audit log page with filtering, plus a chain-integrity indicator (green/red) sourced from
  `/audit-logs/verify` — don't compute or infer integrity client-side, just render what the backend
  returns. See `07-AUDITING-GUIDE.md` for what "verify" means.
- Supervisor escalation queue.

Both: agree on a shared design system pass before splitting further — check `frontend-design` guidance
for typography/layout choices so the two views don't visibly diverge in style.

## 5. Data flow this app sits in

This app **only reads and writes through the API contract** in the project doc §4. It never talks to
Postgres, Redis, or the ML endpoint directly. Every number on the executive dashboard (downtime avoided,
cost saved) is computed backend-side from `downtime_windows` and lifecycle events — if a number looks
wrong, the fix is in the backend aggregation, not a frontend calculation layered on top.

## 5a. Auditing note

The audit log page is read-only in a stronger sense than the rest of the dashboard: there's no edit
or delete affordance anywhere near it, by design — the backend enforces insert-only at the database
level (`07-AUDITING-GUIDE.md`), and the UI shouldn't even suggest correction is possible. If a
correction workflow is ever needed, it's a new "superseding entry" action, not an edit button.

## 6. AI context block (paste this into your assistant when working on this track)

```
I'm building the Next.js frontend for MaintainNexus, a predictive-maintenance dashboard.
Two role-gated views: engineer (per-station technical dashboard, approve/reject work orders,
risk-driver display) and executive (read-only downtime/cost rollup). A third supervisor view
shares the engineer shell plus an escalation queue.

Hard constraints:
- I only call the documented FastAPI contract (auth, work-orders, dashboard, events endpoints
  under /api/v1/). I never invent an endpoint or compute business metrics client-side that the
  backend should compute (downtime, cost saved, risk score).
- RBAC is enforced server-side; my frontend role-gating is UX only, not the real security boundary.
- Live updates come from SSE/WebSocket against /api/v1/events, not polling.
- Use server components to fetch role-scoped data server-side where practical.
- The audit log page never offers edit/delete — those tables are insert-only server-side, and I
  render (not compute) the chain-integrity status from /audit-logs/verify.
Help me build against this contract precisely — if I ask for something outside it, flag that first.
```
