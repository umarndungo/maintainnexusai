# Integrations Implementation Guide

**Owners:** Integrations track owner(s) — split across mobile offline-sync and notifications/auth
**Reads:** `00-PROJECT-DOC.md` §3–4 before starting.

---

## 1. Scope

Three integration surfaces that don't fit neatly in Frontend/Backend but connect them:

1. **Flutter mobile app — offline-first rework** for technicians.
2. **SMS notifications** (technician dispatch, escalation alerts).
3. **Auth/RBAC as consumed by clients** — how Next.js and Flutter both actually use the JWT from
   `/api/v1/auth/login`.

## 2. Mobile offline-first (owner: whoever owns mobile)

**Why:** technicians work near loading arms/pumps — exactly where connectivity is worst. The app must
be usable with no signal and reconcile once back online.

- Local store as source of truth for the technician's assigned work orders (Isar or Drift — pick one
  and use it consistently, don't mix local-storage approaches across screens).
- Background sync queue: status updates (accepted, in-progress, completed) made offline get queued
  locally and pushed to `PATCH`/`POST /api/v1/maintenance/work-orders/...` once connectivity returns.
- Conflict handling: if a work order was reassigned or escalated server-side while the technician was
  offline, the sync step must surface that conflict to the technician clearly, not silently overwrite
  either side.
- Fallback channel: since this is also the SMS recipient, a technician with zero data connectivity
  still gets the initial dispatch notice via SMS even if the app itself can't sync yet.
- Keep the existing `--dart-define=API_BASE_URL=...` configurability — offline mode doesn't change how
  the backend URL is set, only how aggressively the app defers hitting it.

## 3. SMS notifications (owner: whoever isn't on mobile)

- Backend calls `POST /api/v1/notifications/sms` internally (see Backend guide) on: work-order dispatch
  (to the assigned technician) and escalation (to the supervisor).
- Pick a provider (e.g. Twilio) and wrap it behind that one internal endpoint — don't call the provider
  SDK from multiple places in the codebase.
- Log every send attempt to `sms_log` (project doc §5) with delivery status — this matters for the
  audit trail and for debugging "technician says they never got the alert." `sms_log` doesn't need
  the full hash-chain treatment (`07-AUDITING-GUIDE.md`) since it's operational logging rather than
  a safety/compliance record, but it should still be insert-only — no code path should update a
  past delivery-status row, only append a new attempt if retrying.
- Message content should be short and actionable: equipment, station, urgency, and a link/deep-link
  into the mobile app if the app is installed.

## 4. Auth/RBAC as consumed by clients

- Both Next.js and Flutter call `POST /api/v1/auth/login` and store the returned JWT (Next.js: httpOnly
  cookie via a server action/route handler, not localStorage; Flutter: secure storage, not shared prefs).
- Both call `GET /api/v1/auth/me` on session start to get role + station scoping, and use that only to
  drive UI — the actual enforcement is server-side (Backend guide §2 step 2), so a client bug here is a
  UX problem, not a security hole, but it should still be correct.
- Token refresh strategy: agree on one approach (short-lived JWT + refresh token, or long-lived JWT with
  reasonable expiry) between mobile and web rather than each picking independently, since both hit the
  same `/auth` endpoints.

## 5. Tasks

- **Mobile owner**: offline local store + sync queue + conflict surfacing in the mobile app; SMS
  deep-link handling on the receiving end.
- **Notifications/auth owner**: SMS provider integration behind the internal endpoint + `sms_log`;
  help define the shared token storage/refresh approach with both Frontend and mobile.

## 6. AI context block

```
I'm working on integrations for MaintainNexus: offline-first sync for the Flutter technician app,
SMS notifications (dispatch + escalation), and how both Next.js and Flutter clients consume JWT
auth from a shared FastAPI backend.

Hard constraints:
- Mobile local storage is the source of truth while offline; a background queue syncs status changes
  once connectivity returns, and any server-side conflict (reassignment/escalation while offline) is
  surfaced to the technician, never silently overwritten.
- SMS sending goes through exactly one internal backend endpoint (POST /api/v1/notifications/sms) —
  no provider SDK calls scattered elsewhere, and every send is logged for the audit trail.
- Tokens are stored securely (httpOnly cookie for web, secure storage for mobile) — never
  localStorage or shared prefs.
- Client-side role checks are UX convenience only; the real enforcement is server-side, so I don't
  treat a client fix here as closing a security gap.
Help me implement against these constraints.
```
