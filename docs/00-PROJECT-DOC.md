# MaintainNexus — Updated Project Doc

**Date:** 2026-09-11
**Status:** Active build — Phase 2 (predictive scoring, approval workflow, RBAC, Next.js dashboard, offline mobile)

---

## 1. What this system does

MaintainNexus watches high-wear depot equipment — loading arms, pumps, valves — and moves maintenance
from *reactive* to *condition-based*. Telemetry comes in, a risk model scores it, and if risk is high
enough the system opens a work order, routes it through engineer approval, dispatches a certified
technician, and tracks the whole thing to closure without anyone losing visibility into downtime or cost.

**Core goal:** more throughput and more automation must not cost safety or equipment lifespan. Every
design decision below should be checked against that — if a shortcut makes the system faster but hides
risk from an engineer, it's the wrong shortcut.

---

## 2. Architecture (Phase 2)

```
Sensors / simulated telemetry
        │
        ▼
POST /api/v1/alerts/telemetry  ──validate──▶  Celery task queue (Redis)
                                                     │
                                                     ▼
                                    ML risk scoring (POST /api/v1/ml/predict-risk)
                                                     │
                                        risk ≥ threshold?
                                          │yes              │no
                                          ▼                 ▼
                              Create work order        drop / log only
                              status = PENDING_APPROVAL
                                          │
                                          ▼
                         Notify engineer-in-charge (dashboard + push/SMS)
                                          │
                       ┌──────────────────┼──────────────────┐
                       ▼                  ▼                  ▼
                  APPROVED           REJECTED         no action in SLA window
                       │                                     │
                       ▼                                     ▼
          find technician + check parts                 ESCALATED → supervisor
                       │
                       ▼
                  DISPATCHED  ──▶ technician mobile app (offline-first)
                       │
                       ▼
                  IN_PROGRESS → COMPLETED
                       │
                       ▼
          Audit log + downtime window closed + dashboards update (SSE/WebSocket)
```

Three front ends sit on top of one backend contract:

- **Next.js web dashboard** — engineer (per-station technical view) and executive (value/downtime view) roles.
- **Flutter mobile app** — technician role, offline-first.
- **Backend (FastAPI)** — single source of truth, owns RBAC, lifecycle, ETL, and the ML scoring call.

---

## 3. Roles and what each one sees

| Role | Primary surface | Sees | Can do |
|---|---|---|---|
| Technician | Mobile app (offline-first) | Assigned work orders, equipment location, parts needed | Accept, update status, mark complete, view own history |
| Engineer (station) | Next.js dashboard | All telemetry/alerts for their station(s), risk drivers, pending approvals | Approve/reject work orders, view station-level audit log |
| Executive | Next.js dashboard | Cross-station rollups: downtime avoided, cost saved, uptime trend | Read-only |
| Supervisor | Next.js dashboard (shared engineer view + escalation queue) | Escalated work orders past SLA | Reassign, force-approve, close |

RBAC is enforced **server-side** on every endpoint — the frontend hiding a button is UX, not security.

---

## 4. API contract (single source of truth — every guide below references these exact paths)

### Existing (keep as-is)
| Method | Path | Consumed by |
|---|---|---|
| POST | `/api/v1/alerts/maintenance` | backend-internal, integrations |
| POST | `/api/v1/alerts/telemetry` | sensor ingestion / simulator |
| GET | `/api/v1/hr/technicians/available` | backend (dispatch step), engineer dashboard |
| GET | `/api/v1/warehouse/stock` | backend (dispatch step), engineer dashboard |
| POST/GET | `/api/v1/maintenance/work-orders` | backend, mobile, dashboard |
| GET | `/api/v1/alerts/recent` | dashboard |
| GET | `/api/v1/dashboard/summary` | dashboard (executive rollup) |
| GET | `/api/v1/dashboard/audit-logs` | dashboard |
| GET | `/api/v1/dashboard/audit-logs/verify` | dashboard (integrity check), compliance/manual use |

### New (Phase 2 — build these)
| Method | Path | Purpose | Consumed by |
|---|---|---|---|
| POST | `/api/v1/ml/predict-risk` | Score telemetry, return risk + top contributing features | ETL pipeline (server-side only) |
| PATCH | `/api/v1/maintenance/work-orders/{id}/approve` | Engineer approves | Next.js engineer view |
| PATCH | `/api/v1/maintenance/work-orders/{id}/reject` | Engineer rejects | Next.js engineer view |
| PATCH | `/api/v1/maintenance/work-orders/{id}/escalate` | System-triggered on SLA breach; supervisor can also manually escalate | Celery Beat job, Next.js supervisor view |
| GET | `/api/v1/maintenance/work-orders/{id}/lifecycle` | Full persisted transition history | Next.js (both views), mobile detail screen |
| GET | `/api/v1/dashboard/equipment/{id}/downtime` | Per-equipment downtime windows | Next.js engineer view |
| GET | `/api/v1/dashboard/executive-summary` | Downtime avoided, cost saved, uptime trend | Next.js executive view |
| POST | `/api/v1/auth/login` | Issue JWT | All three front ends |
| GET | `/api/v1/auth/me` | Current user + role + permitted stations | All three front ends |
| GET/WS | `/api/v1/events` | SSE or WebSocket stream for live dashboard updates | Next.js dashboard |
| POST | `/api/v1/notifications/sms` | Internal — triggers SMS to technician/engineer | Backend-internal only (integrations) |

**Rule for every team:** if you need a field the contract above doesn't have, add it to this table first
and flag it in standup — don't invent a shadow endpoint or a client-side workaround.

---

## 5. Data model additions (Postgres)

- `equipment` — id, station_id, type (loading_arm/pump/valve), install_date, last_service_date
- `work_order_lifecycle_events` — id, work_order_id, from_status, to_status, actor_id, actor_role, timestamp, note
  *(this replaces the currently-undocumented, non-persisted lifecycle gap flagged in the original progress doc)*
- `users` — id, name, role, station_ids[], phone (for SMS), push_token
- `sms_log` — id, work_order_id, recipient, status, sent_at
- `downtime_windows` — id, equipment_id, started_at, ended_at (nullable while open), cause_alert_id

**Auditing note:** `work_order_lifecycle_events` and `audit_logs` are hash-chained (each row stores
`event_hash = SHA256(event_data + previous_event_hash)`) and insert-only at the DB grant level —
see `07-AUDITING-GUIDE.md`. This gives tamper-evidence without needing a distributed ledger, since
there's a single trusted writer (the backend), not multiple mutually-distrusting parties.

---

## 6. Data flow: ingestion → ETL → ML → storage → retrieval

1. **Ingestion**: telemetry lands via `POST /api/v1/alerts/telemetry` (live) or is generated by Celery
   Beat every 5 min (simulated/demo). Validation unchanged (required fields, numeric ranges, timestamp
   sanity) — already implemented, keep it.
2. **ETL (Celery worker)**: validated telemetry → call `/api/v1/ml/predict-risk` → if risk ≥ threshold,
   check `warehouse/stock` for parts → check `hr/technicians/available` → transform into work-order
   payload → **status starts at `PENDING_APPROVAL`, not dispatched**.
3. **ML scoring**: model is a separate concern from the pipeline logic — see Data/ML guide. It must return
   both a score and the top contributing features (for the engineer's "why" view), not just a number.
4. **Storage**: Postgres is the only system of record. Work-order lifecycle is event-sourced
   (`work_order_lifecycle_events`), so current status is *derived*, never hand-edited.
5. **Retrieval**: all three front ends read through the API only — nobody queries Postgres directly.
   Dashboard live-updates come from `/api/v1/events`, not polling, except mobile in offline mode which
   falls back to its local store.

Two data sources must stay separated:
- **Live/production telemetry** — flows through the pipeline above only.
- **Historical/training data (Kaggle or similar)** — lives in its own storage path, used only to train
  and validate the model offline. It never touches the live ETL pipeline.

---

## 7. Team map

| Track | Owner(s) | Guide |
|---|---|---|
| Frontend (Next.js dashboard) | Frontend track owner(s) | `01-FRONTEND-GUIDE.md` |
| Backend (FastAPI, lifecycle, RBAC) | Backend track owner | `02-BACKEND-GUIDE.md` |
| Data/ML (risk model, ETL) | ML track owner | `03-DATA-ML-GUIDE.md` |
| Deployment (Docker, hosting, CI) | Deployment track owner | `04-DEPLOYMENT-GUIDE.md` |
| Pitch deck | Pitch deck owner | `05-PITCH-DECK-GUIDE.md` |
| Integrations (SMS, shared auth strategy) | Integrations track owner | `06-INTEGRATIONS-GUIDE.md` |
| Auditing (tamper-evident logs) | Backend track owner | `07-AUDITING-GUIDE.md` |
| Mobile (Flutter, offline-first) | Mobile track owner | `08-MOBILE-GUIDE.md` |

---

## 8. Known gaps carried over from Phase 1 (must close in Phase 2)

- Work-order and recent-alert list APIs were documented as deduplicating; they don't. Fix when touching
  those handlers for lifecycle work — don't leave it silently wrong twice.
- Lifecycle was documented (`CREATED → PARTS_RESERVED → DISPATCHED`) but never persisted. Phase 2
  replaces this with the event-sourced model in §5 — this is not optional, the escalation timer and
  the executive downtime-avoided metric both depend on it existing.
- `database/scheduler.py` (legacy, non-Docker path) still sends a fixed sample alert — either delete it
  or point it at the same randomized generator Celery Beat uses, so there's one source of demo data, not two.
