# Deployment Implementation Guide

**Owner:** devops track owner
**Reads:** `00-PROJECT-DOC.md` §2, §4 before starting.

---

## 1. Scope

Extend the existing Docker Compose stack (Postgres, Redis, FastAPI, Celery worker, Celery Beat) to
support: the new ML scoring service, the Next.js dashboard, and a build/release path for the Flutter
mobile app. Add the escalation scheduler's dependency (already covered by Celery Beat, just confirm
timing) and SMS provider credentials as secrets, not code.

## 2. Compose service additions

| Service | Notes |
|---|---|
| `ml-service` | Serves `/predict-risk`. Can be a separate container or a module inside the API initially — but give it its own health check either way so it can be scaled/redeployed independently later. |
| `web` (Next.js) | Build with `output: 'standalone'` for a small container image. Needs `API_BASE_URL` and the auth/JWT config as env vars, same pattern as the existing `--dart-define=API_BASE_URL` approach for Flutter. |
| existing: postgres, redis, api, worker, beat | Keep as-is; add the new tables via the existing safe-migration pattern already used for `alert_task_id`. The migration for `work_order_lifecycle_events`/`audit_logs` must also revoke UPDATE/DELETE grants on those tables for the app's DB role (`07-AUDITING-GUIDE.md`) — this is a permissions change, not just a schema change, so include it explicitly in the migration review rather than assuming the schema diff covers it. |

## 3. Environment/config discipline

- One `.env.example` per service, checked in; real secrets (SMS provider key, JWT signing secret,
  DB credentials) never committed.
- `API_BASE_URL` must be the *one* place every frontend (Next.js and Flutter) points to — don't let
  either hardcode a host.
- CORS: currently enabled for local Flutter Web dev — update the allowed-origins list to include the
  Next.js dev/staging/prod origins and drop the Flutter-Web-specific origin once that target is retired.

## 4. Hosting

- Next.js dashboard: standard Node hosting (Vercel or a container behind the same reverse proxy as the
  API) — this replaces the previously-documented Netlify/GitHub-Pages-for-Flutter-Web approach, since
  that was static-hosting-specific and Next.js needs a server runtime for the parts of this app that
  use server components/SSR.
- Flutter mobile: standard app store / internal distribution build pipeline (see Integrations guide for
  the offline-sync implications on build config).
- Backend + ML service + Postgres + Redis: keep on the same host/cluster as today unless load testing
  says otherwise — don't split them preemptively.

## 4a. Audit chain verification job

Celery Beat gets one more scheduled job (alongside the existing 5-min telemetry generator and the
new escalation-SLA scan): walking the `work_order_lifecycle_events` and `audit_logs` hash chains and
alerting on mismatch (`07-AUDITING-GUIDE.md` §3). This is a read-only job — it doesn't need new
infrastructure, just a new periodic task registered on the existing `beat` service. Wire its alert
output to whatever channel the team already watches for pipeline failures; don't stand up a separate
notification path just for this.

## 5. CI tasks

- Backend: run the existing test suite (flag the missing `prometheus-client` dependency issue from
  Phase 1 — make sure CI installs from `requirements.txt` cleanly, not just the local dev env) plus new
  tests for lifecycle-event persistence, RBAC denial paths, and audit-chain integrity (write a test
  that asserts a direct UPDATE/DELETE against the app's DB role actually fails, not just that the
  application code doesn't attempt one — the grant revocation is the real control).
- Frontend: typecheck + lint + build on every PR; add at least a smoke test hitting a mocked
  `/auth/me` + `/dashboard/summary` before merging role-gating changes.
- Mobile: `flutter analyze` (already passing per Phase 1 notes) — also replace the currently
  commented-out widget test file with at least one real test before this ships, since "no runnable
  test" shouldn't carry into a release build.

## 6. Tasks

- Add `ml-service` + `web` to `docker-compose.yml`, wire env vars and health checks.
- Set up secrets management for SMS provider + JWT signing key (whatever the hosting target's secret
  store is — don't put these in `.env` files that get committed).
- Update CORS config for the new frontend origin.
- Include the audit-table permission revocation in the migration review checklist, not just the
  schema diff.
- Set up CI pipeline stages per §5.
- Confirm and document the mobile app release/distribution process with the Integrations owner.

## 7. AI context block

```
I'm handling deployment for MaintainNexus, a predictive-maintenance system with a FastAPI backend,
Postgres, Redis/Celery, a separate ML scoring service, a Next.js web dashboard, and a Flutter
offline-first mobile app.

Hard constraints:
- All services are defined in one Docker Compose stack for now; don't split services onto separate
  infrastructure without a stated load-testing reason.
- Every frontend (web and mobile) reads its backend URL from one configurable env var — never
  hardcoded.
- Secrets (SMS provider keys, JWT signing secret, DB credentials) are never committed — env-var or
  secret-store only.
- Audit-table migrations include a DB-level grant change (revoke UPDATE/DELETE for the app role) —
  I treat that as part of the migration, not an optional follow-up.
- CI must install dependencies from the checked-in requirements/lockfiles cleanly — a passing test
  suite in someone's local env that fails in a clean install is treated as a broken build.
Help me build and configure this deployment against those constraints.
```
