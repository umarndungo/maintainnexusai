# Backend Implementation Guide — FastAPI

**Owner:** backend track owner
**Reads:** `00-PROJECT-DOC.md` §4–6 before starting. This guide is the backend's half of that contract.

---

## 1. Scope

- Persist work-order lifecycle as events (closes the biggest Phase 1 gap).
- Add RBAC middleware/dependency across all routers.
- Add the escalation scheduler job.
- Keep ML scoring behind the internal `/api/v1/ml/predict-risk` integration boundary. The endpoint
   calls the trained XGBoost artifact, returns the shared risk contract, and requires
   `X-Internal-Service`. Live ETL calls it through `etl/ml_client.py`; training data remains offline.
- Add per-equipment downtime tracking and the executive-summary aggregation.
- Add auth (`/login`, `/me`) issuing JWTs with role + station claims.
- Add the authenticated live-events endpoint as SSE. The legacy unauthenticated WebSocket route was
   removed; use `/api/v1/events` for dashboard updates.

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
5. `POST /api/v1/ml/predict-risk` — internal-only model adapter returning `risk_score`, `risk_level`,
   `top_features`, `prediction_horizon_hours`, `model_version`, `prediction_id`, and `timestamp`.
   The Celery worker calls this endpoint through `etl/ml_client.py`; the FastAPI telemetry handler
   never makes the scoring request synchronously.
6. `downtime_windows` table — open a window when a work order enters `DISPATCHED` for equipment
   currently up, close it when lifecycle reaches `COMPLETED`. This is what both the equipment-downtime
   endpoint and the executive summary read from.
7. `GET /api/v1/dashboard/equipment/{id}/downtime`, `GET /api/v1/dashboard/executive-summary` —
   pure aggregation reads over lifecycle events + downtime windows.
8. Celery Beat job: scan `PENDING_APPROVAL` work orders older than the SLA window (project doc says
   ~2 hrs) → call the escalate transition automatically.
9. `GET /api/v1/events` — SSE stream of lifecycle transitions and new alerts, scoped by the
   requester's role/stations (don't broadcast everything to everyone).
10. `POST /api/v1/notifications/sms` — internal only, called by the pipeline on dispatch/escalation;
    see Integrations guide for the actual provider call.
11. Apply the same hash-chain treatment to the existing `audit_logs` table (same columns, same
    insert-only grant revocation) — it predates this phase but needs to meet the same bar.
12. **Follow-up:** add a Celery Beat chain-verification job and
   `GET /api/v1/dashboard/audit-logs/verify`. The current release writes chained rows but does not
   yet expose scheduled or on-demand verification.

## 3. Fix while you're in here (Phase 1 known gaps)

- Work-order and recent-alert list endpoints should deduplicate by alert task ID / work-order ID when
   the list handlers are next revised.
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
and auth; the ETL pipeline uses the internal service header for work-order dispatch. `/notifications/sms`
is internal-only. ML scoring is available only through the internal service boundary and must not be
exposed to end-user roles.

## 5. Data flow ownership

You own ingestion, ETL orchestration, storage, and retrieval APIs. Telemetry ingestion validates and
queues data quickly; Celery owns the scoring request and subsequent alert processing. You do **not** own the model itself.
The model call and `top contributing features` contract remain deferred until the ML service owner
provides a stable request/response specification.

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
