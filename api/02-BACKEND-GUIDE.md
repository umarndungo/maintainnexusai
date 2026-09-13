# Backend Implementation Guide — FastAPI

**Owner:** backend track owner
**Reads:** `00-PROJECT-DOC.md` §4–6 before starting. This guide is the backend's half of that contract.

---

## 1. Scope

- Persist work-order lifecycle as events (closes the biggest Phase 1 gap).
- Add RBAC middleware/dependency across all routers.
- Add the escalation scheduler job.
- Wire the ML scoring call into the ETL pipeline (call out, don't reimplement the model here — see
  Data/ML guide for the model itself).
- Add per-equipment downtime tracking and the executive-summary aggregation.
- Add auth (`/login`, `/me`) issuing JWTs with role + station claims.
- Add the live-events endpoint (SSE recommended over WebSocket unless mobile also needs bidirectional
  push — confirm with Integrations track before committing).

## 2. New/changed endpoints — build in this order

1. `POST /api/v1/auth/login`, `GET /api/v1/auth/me` — everything else needs a role to check against.
2. RBAC dependency (FastAPI `Depends`) applied to every existing router — technician, engineer,
   executive, supervisor scopes as defined in project doc §3.
3. `work_order_lifecycle_events` table + migration. Rewrite work-order creation/update to write events;
   derive current status from the latest event rather than storing status as a mutable column that can
   drift from the log. Build this **with the hash-chain columns from the start** (`event_hash`,
   `previous_event_hash`, `supersedes_event_id`) rather than retrofitting later — see
   `07-AUDITING-GUIDE.md` for the exact chaining scheme. Revoke UPDATE/DELETE grants on this table for
   the application DB role in the same migration.
4. `PATCH .../approve`, `.../reject`, `.../escalate` — each just appends a lifecycle event and, on
   approve, continues the existing dispatch logic (technician lookup + parts check, already built).
5. `POST /api/v1/ml/predict-risk` — thin proxy/client to the model service (see Data/ML guide for
   what it returns). ETL pipeline calls this in place of whatever inline scoring exists now.
6. `downtime_windows` table — open a window when a work order enters `DISPATCHED` for equipment
   currently up, close it when lifecycle reaches `COMPLETED`. This is what both the equipment-downtime
   endpoint and the executive summary read from.
7. `GET /api/v1/dashboard/equipment/{id}/downtime`, `GET /api/v1/dashboard/executive-summary` —
   pure aggregation reads over lifecycle events + downtime windows.
8. Celery Beat job: scan `PENDING_APPROVAL` work orders older than the SLA window (project doc says
   ~2 hrs) → call the escalate transition automatically.
9. `GET/WS /api/v1/events` — SSE stream of lifecycle transitions and new alerts, scoped by the
   requester's role/stations (don't broadcast everything to everyone).
10. `POST /api/v1/notifications/sms` — internal only, called by the pipeline on dispatch/escalation;
    see Integrations guide for the actual provider call.
11. Apply the same hash-chain treatment to the existing `audit_logs` table (same columns, same
    insert-only grant revocation) — it predates this phase but needs to meet the same bar.
12. Celery Beat job: walk both chains (`work_order_lifecycle_events`, `audit_logs`) from genesis and
    verify every hash on a schedule; alert on any mismatch. Back this with
    `GET /api/v1/dashboard/audit-logs/verify` for on-demand checks from the frontend.

## 3. Fix while you're in here (Phase 1 known gaps)

- Work-order and recent-alert list endpoints claim deduplication in the README but don't do it —
  add explicit dedup (by alert task ID / work order ID) when you touch these handlers for lifecycle work.
- Delete or fix `database/scheduler.py` so there's one source of demo telemetry, not two diverging ones.

## 3a. Auditing — see the dedicated guide

Steps 3, 11, and 12 above are the auditing feature. Full rationale (why hash-chaining instead of
blockchain), the exact chain scheme, and the DB-grant enforcement details are in
`07-AUDITING-GUIDE.md` — read it before writing the migration, since the hash-chain columns need to
be right the first time (retrofitting a chain onto existing rows means picking a point to call
"genesis" for already-live data, which is messier than starting clean).

## 4. Who consumes what you build

Every endpoint you add is already listed with its consumer in project doc §4. Concretely:
Next.js hits the auth, work-order action, and dashboard endpoints; Flutter mobile hits work-orders
(read + status update) and auth; the ETL pipeline itself is the only caller of `/ml/predict-risk`
and `/notifications/sms` — those two are internal-only, don't expose them to a public role scope.

## 5. Data flow ownership

You own steps 1–4 and 6 of the pipeline in project doc §6 (ingest, ETL orchestration, storage,
retrieval API). You do **not** own the model itself — you own the contract for calling it
(`predict-risk` request/response shape) and integrating its output into the work-order payload,
specifically surfacing the "top contributing features" field so the frontend can render risk drivers
without needing to know anything about the model internals.

## 6. AI context block

```
I'm building the FastAPI backend for MaintainNexus, a predictive-maintenance and work-order
dispatch system. Phase 2 adds: event-sourced work-order lifecycle (never a mutable status column),
RBAC across all routers (technician/engineer/executive/supervisor scopes), an escalation scheduler
for approvals stuck past an SLA, a call-out to a separate ML risk-scoring endpoint (I don't own the
model, only the integration), per-equipment downtime tracking, and a live SSE/WebSocket events feed.

Hard constraints:
- Work-order status is always derived from work_order_lifecycle_events, never written directly.
- Every endpoint is gated by role; the frontend hiding UI is not a substitute for this.
- /ml/predict-risk and /notifications/sms are internal-only — not exposed to end-user roles.
- Live/production telemetry and historical training data are separate paths; the live ETL pipeline
  never touches training data.
- work_order_lifecycle_events and audit_logs are hash-chained and insert-only at the DB grant
  level — I never write UPDATE or DELETE against them, even for corrections; corrections are new
  rows with supersedes_event_id set. Full scheme in 07-AUDITING-GUIDE.md.
Help me implement against this precisely, and flag if a request would violate one of these constraints.
```
