# Prompt: Add username/password auth + seed default credentials

Paste everything below the line into a fresh AI coding session pointed at the
`maintainNexus` repo (branch `feature/integrations` or later).

---

## Context

This is a FastAPI backend (`api/`) + SQLAlchemy/Postgres (`database/`) +
Flutter mobile app (`technician-mobile-app/`) + Next.js web app (`web/`)
called MaintainNexus. Authentication today is **passwordless**:

- `api/auth.py` defines a static `USERS` dict keyed by a `user_id` string
  (`tech-demo`, `engineer-demo`, `supervisor-demo`, `executive-demo`), each
  mapping to `{name, role, station_ids, technician_id?}`.
- `POST /api/v1/auth/login` takes `{"user_id": "..."}` — no password field —
  looks the id up via `_lookup_user()`, and returns a signed token.
- `_lookup_user()` checks `USERS` first, then falls back to the HR
  technician roster (`api/technicians.py`'s `TECHNICIANS_BY_ID`, ids
  `TECH-101` .. `TECH-120`), synthesizing a `role: "technician"` user record
  on a roster hit. This was added recently so a raw roster id is itself a
  valid login — **do not remove this fallback**, the mobile app depends on
  it for "my work orders" scoping (see `AppController.technicianId` in
  `technician-mobile-app/lib/state/app_controller.dart`).
- The token itself is a hand-rolled HMAC-signed JWT-lookalike
  (`create_access_token` / `get_current_user` in `api/auth.py`) — it only
  ever carries `{sub, exp}`; everything else is re-resolved from `_lookup_user()`
  on every request. **Keep this token format** — nothing downstream should
  need to change because of this task.
- `api/technicians.py`'s `TECHNICIANS` roster (20 technicians, `TECH-101`
  through `TECH-120`) is generated **in-memory at import time** with
  `random.choice()` for cert sets — it is **not persisted** and regenerates
  differently on every process restart (see the wiki's Known-Gaps page,
  "In-memory inventory & technician roster"). This is a problem for
  password auth: a credential row keyed to `TECH-105` needs `TECH-105` to
  reliably exist and mean the same thing across restarts. **You must fix
  this as part of this task** — see Task 1 below.
- No password hashing library is installed yet (`requirements.txt` has no
  `bcrypt`/`passlib`/`argon2`).
- There is no Alembic. Schema changes follow the existing convention in
  `database/run_migrations.py`: new tables are added to
  `database/models.py` and picked up by `Base.metadata.create_all()`;
  additive columns on *existing* tables get an explicit
  `ALTER TABLE ... ADD COLUMN` guarded by an `inspector.get_columns()`
  check in `_ensure_legacy_columns()` (same file). Follow this pattern —
  do not introduce Alembic.

## Goal

Replace the passwordless login with real `user_id` + `password`
authentication, and seed default credentials for:

- **20 technicians** — must line up 1:1 with the existing roster ids
  `TECH-101`..`TECH-120` (do not invent new ids for these).
- **3 engineers** — new ids, e.g. `ENG-1`, `ENG-2`, `ENG-3`.
- **3 supervisors** — new ids, e.g. `SUP-1`, `SUP-2`, `SUP-3`.
- **3 executives** — new ids, e.g. `EXEC-1`, `EXEC-2`, `EXEC-3`.

Keep the four existing demo logins (`tech-demo`, `engineer-demo`,
`supervisor-demo`, `executive-demo`) working — they're referenced in the
wiki, `Getting-Started.md`'s curl examples, and test fixtures. Give them
passwords too rather than deleting them.

This is an **end-to-end** auth task, not just the login call: it also
covers a real change-password flow (backend endpoint + a screen on each
platform), since a seeded default password is worthless if nobody can
ever change it. See Task 6 and Task 7.

## Task 1 — make the technician roster stable across restarts

Pick one of these two approaches (pick the smaller one unless you have a
reason not to — this codebase's own comments favor "the smaller diff that
still fixes the actual problem"):

**A. Deterministic generation (minimal diff).** Seed `random` with a fixed
value before generating `_TECHNICIAN_NAMES`/`_CERT_SETS` in
`api/technicians.py::_generate_technicians()`, so the roster is identical
every process start (same names, same certs, same `on_shift` pattern).
`TECH-101`..`TECH-120` then always mean the same person. This does not
require a DB table for the roster itself — only credentials need to persist.

**B. Persist the roster in Postgres.** Add a `TechnicianRecord` table to
`database/models.py` mirroring the current in-memory shape (`id`, `name`,
`on_shift`, `certs` as a JSON/ARRAY column, `phone_number`,
`non_smartphone`), seed it once, and have `api/technicians.py` read from
the DB instead of generating in-process. More correct long-term, bigger
diff — only do this if the DB seeding infrastructure you're about to build
for Task 2 makes it nearly free.

State which one you picked and why in your final summary.

## Task 2 — add a persisted credentials table

Add a new SQLAlchemy model to `database/models.py`, e.g.:

```python
class StaffCredential(Base):
    __tablename__ = "staff_credentials"

    user_id = Column(String, primary_key=True)   # "TECH-101", "ENG-1", "tech-demo", ...
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)          # "technician" | "engineer" | "supervisor" | "executive"
    technician_id = Column(String, nullable=True)   # set only for role == "technician"
    must_change_password = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
```

Add `passlib[bcrypt]` (or `bcrypt` directly) to `requirements.txt`. Hash
every seeded password with bcrypt — never store or log plaintext.

Write a one-time seed script (e.g. `database/seed_credentials.py`, run the
same way other one-off scripts in this repo are invoked — check
`database/run_migrations.py`'s `if __name__ == "__main__":` block for the
convention) that:

1. Creates the `staff_credentials` table if missing (via
   `Base.metadata.create_all(engine)`, same as the rest of the schema).
2. Inserts one row per seeded identity (idempotent — skip a `user_id` that
   already has a row, so re-running the seed script is safe).
3. Prints the plaintext default passwords **once, to stdout, during
   seeding only** — this is a demo system, so the "share credentials with
   the team" step is a printed table, not a secrets manager. Never persist
   plaintext anywhere.

### Default password scheme

Pick something the team can actually type during a demo. Suggested
convention — **state whatever you actually pick in your summary so it can
go in the wiki**:

- Technicians: `Tech-<id-number>-2026` (e.g. `TECH-101` → `Tech-101-2026`)
- Engineers: `Eng-<n>-2026` (e.g. `ENG-1` → `Eng-1-2026`)
- Supervisors: `Sup-<n>-2026`
- Executives: `Exec-<n>-2026`
- Existing demo users (`tech-demo`, etc.): reuse their own id as the
  password stem, e.g. `tech-demo` → `TechDemo-2026`, so they're easy to
  remember from the login screen prefill.

Set `must_change_password = True` on every seeded row. Unlike an earlier
draft of this task, you **do** need to build the flow that lets someone
clear it — see Task 6 (backend) and Task 7 (both platforms' UI) below.

## Task 3 — update the login endpoint

In `api/auth.py`:

1. `LoginRequest` gains a required `password: str` field.
2. `_lookup_user()` stays as the *identity* resolver (role, name, station,
   technician_id) — do not fold password checking into it.
3. Add a `_verify_password(user_id: str, password: str) -> dict | None`
   helper: looks up the `StaffCredential` row for `user_id` in the DB
   (open a session the same way other endpoints in this codebase do — see
   `api/workorders.py` for the `SessionLocal` pattern), and returns the
   resolved user dict (via `_lookup_user(user_id)`) only if
   `passlib.context.CryptContext.verify(password, row.password_hash)`
   succeeds. Return `None` on no such row *or* a bad password — same error
   either way, to avoid leaking which usernames exist.
4. `login()` calls `_verify_password()` instead of `_lookup_user()`
   directly, and raises the same `401 "Unknown user"` (or reword to
   `"Invalid credentials"` — your call, just be consistent) on failure.
   Include `must_change_password` (from the `StaffCredential` row) in the
   `user` object of the login response — both platforms' UIs (Task 7)
   branch on this to force the change-password screen right after login.
5. `get_current_user()` (the per-request token check) is unaffected — it
   never re-checks a password, only the signed token. Leave it exactly as
   is.

## Task 4 — tests

Add `tests/test_auth_password_login.py` (or extend
`tests/test_auth_technician_scoping.py`) covering:

- A seeded technician (`TECH-105`) logs in with the correct default
  password and gets back `role: technician, technician_id: TECH-105`.
- The same id with a wrong password gets 401.
- A seeded engineer/supervisor/executive id logs in correctly.
- The existing demo ids (`tech-demo` etc.) still log in with their new
  passwords.
- A seeded login's response has `must_change_password: true`; after a
  successful `PATCH /api/v1/auth/change-password` (Task 6), a fresh login
  for that same id has `must_change_password: false`.
- `PATCH /api/v1/auth/change-password` rejects a wrong `current_password`
  (401) and a `new_password` under the minimum length (422).
- `tests/test_auth_technician_scoping.py`'s existing tests will break once
  `LoginRequest` requires a password — update those call sites too
  (`login(LoginRequest(user_id="tech-demo"))` → add the right password).

Run `pytest tests/ -q` and confirm nothing else regresses (there are 3
pre-existing, unrelated failures in `tests/test_phase2_backend.py` about
`INTERNAL_SERVICE_TOKEN` env values — those are not yours to fix).

## Task 5 — update callers

- `technician-mobile-app/lib/services/api_client.dart`'s `login()` and
  `technician-mobile-app/lib/screens/sign_in_screen.dart` need a password
  field now. The sign-in screen already has a (currently decorative)
  `_passcodeController` prefilled with `'••••••'` and a UI note saying
  "passcode is not verified in this build" — wire it up for real and
  update that note. Also fix the `_idController`'s prefilled default
  (`'TC-1042'`, currently not a valid id at all) to something that will
  actually work, e.g. `'tech-demo'`.
- `web/` — check `web/src/lib/api.ts` (or wherever it calls
  `/api/v1/auth/login`) for the same passwordless call and update it, plus
  whatever login form component collects the `user_id`.
- Update `tests/test_workorder_start_assign.py` and any other test file
  that constructs a user dict by hand (`{"id": "engineer-demo", "role":
  "engineer", ...}`) — those bypass the API layer entirely (they call
  handler functions directly), so they're unaffected by the password
  change and need no edits. Only edits are needed where a test actually
  calls the `/auth/login` HTTP path or the `login()` function.

## Task 6 — backend change-password endpoint

Add `PATCH /api/v1/auth/change-password` to `api/auth.py`, guarded by the
existing `get_current_user` dependency (so it needs a valid bearer token,
same as any other authenticated endpoint — no separate re-auth scheme).

Request body:

```python
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
```

Behavior:

1. Look up the caller's `StaffCredential` row by `user["id"]` (the token
   subject — same value `get_current_user` already resolves).
2. Verify `current_password` against `password_hash` with the same
   `passlib` context Task 3 uses. Wrong current password → `401`.
3. Reject `new_password` shorter than 8 characters → `422` (use a
   pydantic validator on `ChangePasswordRequest`, not a manual `if` in the
   handler — consistent with how this codebase uses pydantic elsewhere).
4. Hash `new_password`, overwrite `password_hash`, set
   `must_change_password = False`, commit.
5. Return `{"status": "ok"}` — no token re-issue needed, since the
   existing token never encoded anything password-related.

This is intentionally a "change your own password while logged in" flow,
not a "forgot password" flow — there's no email/SMS reset step. A seeded
user who forgot their default password gets it re-issued by whoever runs
the seed script (out of scope to build tooling for that here).

## Task 7 — change-password screens (mobile + web)

Both platforms need two entry points into the same backend call: a
**forced** one right after a login where `must_change_password` is true,
and a **voluntary** one reachable from an existing settings/profile
screen.

### Mobile (`technician-mobile-app/`)

- New `lib/screens/change_password_screen.dart` — three fields (current
  password, new password, confirm new password), client-side check that
  the last two match before submitting, error text on a failed submit
  (reuse whatever error-surfacing pattern `sign_in_screen.dart` or
  `close_out_screen.dart` already uses — don't invent a new one).
- `lib/services/api_client.dart` gains
  `Future<void> changePassword(String currentPassword, String newPassword)`
  calling the new `PATCH /api/v1/auth/change-password`, following the
  existing `_patch()` helper's pattern (auth headers, `ApiException` on a
  non-2xx).
- `LoginResult` (added in the earlier "my work orders" scoping task) gains
  a `mustChangePassword` field, parsed the same way `technicianId` is.
- `lib/state/app_controller.dart`: `signIn()` sets a new
  `bool mustChangePassword` field from the login result; add a
  `Future<bool> changePassword(String current, String next)` wrapper
  around `_api.changePassword(...)` (mirrors `submitCloseOut`'s
  try/on ApiException/catch pattern) that clears `mustChangePassword` to
  `false` on success.
- Wiring the forced redirect: check `lib/app.dart` and its
  `_AppRootState` before touching navigation. The wiki's Mobile-App page
  documents a real gotcha here — `MaterialApp.home` is only read once to
  seed the `Navigator`, so a later state change doesn't swap the screen on
  its own, and `_AppRootState` already listens to `AppController` and
  calls `navigator.pushAndRemoveUntil(...)` explicitly for the sign-in ↔
  signed-in transition. Extend that same listener: when
  `signedIn && mustChangePassword`, push `ChangePasswordScreen` instead of
  the normal home shell; on that screen's successful submit, continue on
  to the normal post-login route exactly as if `mustChangePassword` had
  been false to begin with.
- Voluntary entry point: add a "Change password" row to
  `lib/screens/settings_screen.dart` that pushes the same
  `ChangePasswordScreen`.
- Extend `test/widget_test.dart`'s `FakeApiClient` with `changePassword()`
  and a `mustChangePassword` value on its fake `login()`'s `LoginResult`;
  add a widget test for the forced-change redirect (sign in with
  `mustChangePassword: true` → `ChangePasswordScreen` shows, not the work
  orders list) alongside the existing smoke test.

### Web (`web/`)

- The login proxy is `app/api/auth/login/route.ts` (calls the FastAPI
  backend, currently forwards only `user_id`) and the form is
  `app/login/page.tsx`. Add the password field to the form and forward it
  in the proxy's request body.
- Add a mirror proxy route, `app/api/auth/change-password/route.ts`,
  following `app/api/auth/login/route.ts`'s pattern (reads the session
  token the same way, forwards to
  `PATCH {apiBaseUrl()}/api/v1/auth/change-password`).
- Add a change-password form. Two acceptable places — pick one and note
  which in your summary:
  - A section on the existing `app/profile/page.tsx` (it already renders
    account details via `requireSession` and is reachable by every
    logged-in role) — probably the smaller diff.
  - A dedicated `app/change-password/page.tsx`, gated by `requireSession`
    the same way `profile/page.tsx` is.
- Forced-change redirect: after a successful `app/login/page.tsx` submit,
  check the login response for `must_change_password`; if true, redirect
  to the change-password page/section instead of the normal
  post-login destination, and don't allow navigating away until it
  succeeds (a simple redirect-back-if-still-true guard is enough — this
  doesn't need a full route-guard middleware for a demo app).
- Check `lib/session.ts` / `CurrentUser`'s type (used by
  `lib/api.ts`'s `/api/v1/auth/me` call) — if `must_change_password` needs
  to be readable on later page loads (not just right after login) to keep
  enforcing the redirect, thread it through there too.

## Task 8 — docs

Update the GitHub wiki (clone `git@github.com:umarndungo/maintainnexusai.wiki.git`,
same repo the rest of this project's wiki lives in):

- `Getting-Started.md` — replace the passwordless curl example with one
  that includes `password`, and list (or link to) the default credential
  table for all 29 seeded identities (20 technicians + 4 demo + 3 + 3 +
  3... wait, count it yourself and get this right in the actual doc).
- Add a **new** page, e.g. `Default-Credentials.md`, with the full table:
  id, role, default password, whether `must_change_password` is set, plus
  a short note that every seeded account is forced through the
  change-password screen on first login. Link it from `_Sidebar.md` and
  from `Home.md`'s page list.
- `Known-Gaps-and-Roadmap.md` — remove or update the "In-memory inventory
  & technician roster" entry if Task 1 changed that behavior.
- Mention the new `PATCH /api/v1/auth/change-password` endpoint in
  `Backend-API-Reference.md`'s Auth table.
- `Mobile-App.md` — add a short section on the forced/voluntary
  change-password screen, next to the existing Auth bullet under "What's
  real now".

## Constraints / non-goals

- The change-password flow (Task 6/7) is "change your own password while
  signed in" only. Do **not** build a "forgot password" / email-or-SMS
  reset flow, password-strength scoring beyond the length check, rate
  limiting, or account lockout — out of scope for this pass, and the
  seed script is the actual recovery path for a demo account today.
- Do not change the token format (`create_access_token`/`get_current_user`
  in `api/auth.py`) — only the login *entry point* gains a password check.
- Do not remove or weaken `_lookup_user()`'s roster fallback — it's load-
  bearing for the mobile app's per-technician work-order scoping shipped
  in the previous session.
- Do not add real user self-registration, OAuth, SSO, or email/password
  reset flows — out of scope, this is a demo system with a fixed seeded
  roster.
- This is a hackathon/demo project (see the wiki's "Known Gaps &
  Roadmap" page for the general engineering-tradeoffs tone) — bcrypt +
  a plain `staff_credentials` table is the right amount of engineering
  here, not a full identity-provider integration.

## Deliverable checklist (put this in your final summary)

- [ ] Which roster-stability approach (Task 1 A or B) you picked and why
- [ ] `staff_credentials` table added, migration/seed script runs cleanly
      against a fresh DB
- [ ] Exact default-password scheme used, and the full generated table
      (paste it — this is the answer to "what are the login credentials")
- [ ] `api/auth.py` changes (login, `_verify_password`)
- [ ] Mobile app + web app login-field updates
- [ ] `PATCH /api/v1/auth/change-password` endpoint (Task 6)
- [ ] Change-password screen on mobile (forced + voluntary entry points)
      and confirmation the `MaterialApp.home`/Navigator gotcha was
      handled via the listener pattern, not a `home:` rebuild
- [ ] Change-password form on web (forced + voluntary entry points) and
      which of the two placements (profile page vs. dedicated page) you
      picked
- [ ] New/updated tests, `pytest tests/ -q` output, plus the mobile
      `flutter analyze` / `flutter test` output
- [ ] Wiki pages updated (list which ones)
