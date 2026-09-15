# Mobile Implementation Guide — Flutter (Technician App)

**Owner:** Mobile track owner
**Reads:** `00-PROJECT-DOC.md` §2–4 before starting.

---

## 1. Scope

The technician-facing Flutter app, rebuilt offline-first. Web moves to Next.js (`01-FRONTEND-GUIDE.md`);
Flutter's job narrows to this one surface, which is exactly where it matters most — technicians work
next to loading arms and pumps, which is reliably the worst-connectivity part of the depot. The app has
to be fully usable with no signal and reconcile cleanly once back online.

## 2. Why offline-first, specifically

A technician who can't open their work order because the app is waiting on a network call is worse than
no app at all — they'll fall back to a phone call or a paper log, which is exactly what this system is
trying to replace. Offline isn't a degraded mode here; it's the baseline the app is designed around,
with connectivity as the enhancement.

## 3. Architecture

- **Local store as source of truth** for the technician's assigned work orders — use Isar or Drift
  (pick one and use it consistently across every screen; don't let different features drift onto
  different local-storage approaches).
- **Background sync queue**: status updates made offline (accepted, in-progress, completed) get queued
  locally and pushed to the backend once connectivity returns — `PATCH`/`POST
  /api/v1/maintenance/work-orders/...`. The queue must survive an app restart, not just a backgrounding.
- **Conflict handling**: if a work order was reassigned or escalated server-side while the technician
  was offline, the sync step surfaces that conflict clearly — never silently overwrite either side.
  Concretely: on sync, fetch the current server-side lifecycle state via
  `GET /api/v1/maintenance/work-orders/{id}/lifecycle` before pushing a queued update, and if the
  server state has moved in a way that makes the queued update stale (e.g. already escalated to
  someone else), show the technician what happened rather than pushing blind.
- **Fallback channel**: the technician is also the SMS recipient (see `06-INTEGRATIONS-GUIDE.md` §2),
  so the initial dispatch notice still reaches them via SMS even if the app itself can't sync yet.
  A deep link in that SMS should open the app straight to the relevant work order once it's back online.
- **Configurable backend URL**: keep the existing `--dart-define=API_BASE_URL=...` pattern — offline
  mode changes how aggressively the app defers hitting the backend, not how the URL is set.

## 4. Auth on this client specifically

- Call `POST /api/v1/auth/login`, store the JWT in **secure storage** (not shared prefs).
- Call `GET /api/v1/auth/me` on session start for role/station scoping — this drives UI only, the real
  enforcement is server-side (`02-BACKEND-GUIDE.md` §2 step 2).
- Token refresh strategy must match whatever the web client agrees to (short-lived JWT + refresh token,
  or long-lived JWT with reasonable expiry) — coordinate this once with whoever owns the web auth flow
  rather than picking independently, since both hit the same `/auth` endpoints.
- A logged-in-but-offline technician should still be able to see and act on already-synced work orders —
  don't gate the whole app behind a live token-validation call.

## 5. Exact API surface this app consumes

| Endpoint | Used for |
|---|---|
| `POST /api/v1/auth/login` | Login screen |
| `GET /api/v1/auth/me` | Role/station scoping on session start |
| `GET /api/v1/maintenance/work-orders` | Assigned work-order list (cached locally) |
| `GET /api/v1/maintenance/work-orders/{id}/lifecycle` | Conflict check before pushing a queued update; work-order detail screen |
| `PATCH /api/v1/maintenance/work-orders/{id}` (status update) | Sync queue push |

Nothing else — this app doesn't touch approval/escalation/dashboard/ML/audit endpoints. Those are
engineer/executive/supervisor surfaces in the Next.js dashboard.

## 6. Tasks

- Local store schema + sync queue (survives app restart).
- Conflict-detection logic on sync (fetch-then-compare before push).
- Secure token storage + refresh handling.
- SMS deep-link handling on the receiving end (coordinate payload format with Integrations track).
- Replace the currently commented-out widget test file with real tests before this ships
  (`04-DEPLOYMENT-GUIDE.md` §5 flags this as a release blocker, not optional cleanup).

## 7. AI context block

```
I'm building the Flutter technician app for MaintainNexus, offline-first. Technicians work near
loading arms/pumps where connectivity is worst, so the app must be fully usable offline and
reconcile cleanly once back online — offline is the baseline, not a degraded fallback mode.

Hard constraints:
- Local storage (Isar or Drift, used consistently) is the source of truth while offline. Status
  updates queue locally and sync to the backend once connectivity returns.
- Before pushing a queued update, I fetch the current server-side lifecycle state and check for
  conflicts (reassignment/escalation that happened while offline) — if there's a conflict, I surface
  it to the technician, I never silently overwrite either side.
- Tokens go in secure storage, never shared prefs.
- This app only consumes the work-order read/status-update and auth endpoints — it has no business
  calling approval, escalation, dashboard, ML, or audit endpoints; those belong to the web dashboard.
- Client-side role checks are UX convenience only; real enforcement is server-side.
Help me implement against this precisely, and flag if something I ask for would require this app to
call an endpoint outside its actual scope.
```
