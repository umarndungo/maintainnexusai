# Integrations Implementation Guide

**Owner:** Integrations track owner
**Reads:** `00-PROJECT-DOC.md` §3–4 before starting.
**Note:** Flutter mobile offline-first work now has its own guide — `08-MOBILE-GUIDE.md`. This doc
covers what's left: notifications and the cross-client auth strategy.

---

## 1. Scope

Two integration surfaces that connect Frontend, Backend, and Mobile without belonging fully to any one:

1. **SMS notifications** (technician dispatch, escalation alerts).
2. **Auth/RBAC as consumed by clients** — how Next.js and Flutter both actually use the JWT from
   `/api/v1/auth/login`. (Mobile-specific implementation detail lives in `08-MOBILE-GUIDE.md` §4 —
   this section is where the two clients agree on a shared approach.)

## 2. SMS notifications

**Status: implemented** (Build Plan Phase 2/3, `09-SMS-PHOTO-THEME-DEPLOYMENT-NOTES.md`) — provider is
Africa's Talking, wrapped in `integrations/africastalking_client.py`, called from exactly one place
(`api/notifications.py`). `POST /api/v1/notifications/sms` is real; it just no-ops with status
`SKIPPED_NO_CREDENTIALS` until `AFRICASTALKING_USERNAME`/`AFRICASTALKING_API_KEY` are set as host
secrets (never committed). Dispatch call site: `tasks.notify_dispatch`, enqueued from
`api/workorders.py`'s DISPATCHED transition — approve → technician match → parts check (all already
done by that point) → SMS + push in parallel.

The SMS also carries the mobile deep link (`maintainnexus://work-orders/{id}` — enterprise/sideload
distribution, no domain verification needed) so tapping it opens the app straight to the work order,
same outcome as a push, without depending on a Firebase project existing yet.

Non-smartphone technicians (flagged in `api/technicians.py`) get a different message — a numbered
reply prompt ("Reply 1=Accept 3=Complete to WO-xxxx") — and a `pending_sms_prompts` row instead. The
inbound webhook (`POST /api/v1/notifications/sms/inbound`, protected by a `?token=` shared secret —
`AFRICASTALKING_INBOUND_TOKEN`) matches strictly on phone number + the exact echoed code, never "most
recent open prompt," and routes through the same lifecycle-event writer
(`api.workorders.advance_work_order_status`) every other status change uses — see `tests/test_sms_reply.py`.
`tasks.expire_stale_sms_prompts` (Celery Beat, same cadence as `escalate_stale_approvals`) cleans up
abandoned prompts.

- Pick a provider (e.g. Twilio) and wrap it behind that one internal endpoint — don't call the provider
  SDK from multiple places in the codebase.
- Every send attempt is logged to `sms_log` (project doc §5) with delivery status — this matters for the
  audit trail and for debugging "technician says they never got the alert." `sms_log` doesn't need
  the full hash-chain treatment (`07-AUDITING-GUIDE.md`) since it's operational logging rather than
  a safety/compliance record, but it should still be insert-only — no code path should update a
  past delivery-status row, only append a new attempt if retrying.
- Message content should be short and actionable: equipment, station, urgency, and a link/deep-link
  into the mobile app if the app is installed.

## 3. Auth/RBAC as consumed by clients

- Both Next.js and Flutter call `POST /api/v1/auth/login` and store the returned JWT (Next.js: httpOnly
  cookie via a server action/route handler, not localStorage; Flutter: secure storage, not shared prefs).
- Both call `GET /api/v1/auth/me` on session start to get role + station scoping, and use that only to
  drive UI — the actual enforcement is server-side (Backend guide §2 step 2), so a client bug here is a
  UX problem, not a security hole, but it should still be correct.
- Current backend tokens are signed HS256 bearer tokens with a one-hour expiry. Refresh tokens are not
  implemented; agree on a refresh strategy before production deployment.

## 4. Tasks

- **Integrations owner**: SMS provider integration behind the internal endpoint + `sms_log`; define
  the shared token storage/refresh approach with both Frontend (`01-FRONTEND-GUIDE.md`) and Mobile
  (`08-MOBILE-GUIDE.md`).

## 5. AI context block

```
I'm working on integrations for MaintainNexus: SMS notifications (dispatch + escalation), and
defining how Next.js and Flutter clients consume JWT auth from a shared FastAPI backend. Mobile's
own offline-sync implementation is a separate track (08-MOBILE-GUIDE.md) — I coordinate the shared
auth contract with it but don't own its implementation.

Hard constraints:
- SMS sending goes through exactly one internal backend endpoint (POST /api/v1/notifications/sms) —
  no provider SDK calls scattered elsewhere, and every send is logged for the audit trail.
- Tokens are stored securely (httpOnly cookie for web, secure storage for mobile) — never
  localStorage or shared prefs.
- Client-side role checks are UX convenience only; the real enforcement is server-side, so I don't
  treat a client fix here as closing a security gap.
Help me implement against these constraints.
```

