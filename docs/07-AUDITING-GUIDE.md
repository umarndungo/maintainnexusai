# Auditing Implementation Guide

**Owner:** Backend track owner (this is an extension of the lifecycle-events work in `02-BACKEND-GUIDE.md`)
**Reads:** `00-PROJECT-DOC.md` §5–6 before starting.

---

## 1. Decision: hash-chained append-only log, not blockchain

**Why not blockchain:** blockchain solves consensus among mutually-distrusting parties with no central
authority. MaintainNexus has one writer — the backend — and one organization's data. There's no
consensus problem here, so a real blockchain (even a permissioned one like Hyperledger Fabric) would
add node management, consensus overhead, and complexity that buys nothing over the simpler approach
below. Revisit this only if a genuine multi-party trust requirement shows up — see §5.

**What we actually need:** tamper-evidence (edits are detectable), completeness (deletions are
detectable), and non-repudiation (an approval/rejection can't later be denied). A hash-chained
append-only log gives all three with no new infrastructure.

## 2. How the hash chain works

Every row in `work_order_lifecycle_events` and `audit_logs` gets an additional column:

```
event_hash = SHA256(event_data_serialized + previous_event_hash)
```

- `event_data_serialized` is a canonical (stable field order) JSON or concatenation of the row's own
  fields (excluding `event_hash` itself).
- `previous_event_hash` is the `event_hash` of the immediately prior row **in the same table**
  (a single global chain, not per-work-order — this makes cross-record tampering detectable too, e.g.
  someone can't quietly reorder or backdate events between different work orders).
- The very first row in each table chains from a fixed genesis constant (e.g. `"GENESIS"`).

Any edit to a past row's data changes that row's hash, which breaks every subsequent row's hash —
walking the chain from genesis to the latest row and recomputing detects this immediately.

## 3. Enforcement — this is the part that actually matters

The hash chain only proves tampering *if mutation is otherwise impossible or itself detectable*:

- Revoke `UPDATE` and `DELETE` grants on `work_order_lifecycle_events` and `audit_logs` at the
  Postgres role level for the application's DB user — the API should only ever `INSERT`.
- If a correction is genuinely needed (e.g. a data-entry mistake), it must be a **new row** that
  references and supersedes the old one — never an edit to history. Add a `supersedes_event_id`
  column for this rather than ever touching a past row.
- Run periodic verification (a scheduled Celery Beat job, reusing the existing 5-min scheduler
  pattern) that walks the chain and alerts if any hash fails to match — this is what
  `GET /api/v1/dashboard/audit-logs/verify` exposes on demand, and it's also what should run
  automatically so a break is caught within minutes, not discovered during a compliance review months later.

## 4. Optional external anchoring

For a stronger guarantee that even a compromised database admin couldn't rewrite the whole chain and
recompute new hashes undetected, periodically publish just the **latest chain hash** somewhere outside
your own database — a scheduled export to a separate append-only store you don't control day-to-day
(e.g. a compliance team's own system, a timestamping service, or even a periodic signed email digest).
This borrows blockchain's "anchor to something external" idea without needing a ledger — you're only
ever publishing one small hash value on a schedule, not every event.

This is a nice-to-have for Phase 2. Recommend it as a fast-follow rather than blocking launch on it.

## 5. When to actually reconsider blockchain

Flag this to the team if either becomes true:
- A regulator, insurer, or partner depot operator needs to independently verify maintenance records
  **without trusting your organization's database at all** — i.e., they need write access to their
  own copy of the ledger, not just read access to your API.
- Multiple independent companies each operate equipment and need a shared record none of them can
  unilaterally alter — that's a genuine multi-party trust problem a permissioned ledger is built for.

Until one of those is true, the hash-chained log above gives the same tamper-evidence at a fraction
of the operational cost.

## 6. Tasks

- Add `event_hash` and `previous_event_hash` columns to `work_order_lifecycle_events` and `audit_logs`
  (migration, following the existing safe-migration pattern used for `alert_task_id`).
- Add `supersedes_event_id` (nullable) for correction-as-new-row handling.
- Revoke UPDATE/DELETE grants on both tables for the application DB role.
- Implement chain-write logic in the same place lifecycle events are already being written
  (`02-BACKEND-GUIDE.md` step 3) — don't create a second code path for this.
- Add the Celery Beat verification job + `GET /api/v1/dashboard/audit-logs/verify` endpoint.
- Decide with the team whether external anchoring (§4) ships in Phase 2 or is deferred.

## 7. AI context block

```
I'm adding tamper-evident auditing to MaintainNexus's work-order lifecycle and audit-log tables.
We deliberately chose a hash-chained append-only log over blockchain, because there's a single
trusted writer (our own backend) and no multi-party consensus problem to solve — blockchain's
complexity wouldn't buy anything here.

Hard constraints:
- Each row stores event_hash = SHA256(row_data + previous_row's event_hash), chained globally
  within each table from a fixed genesis value.
- The application's DB role has INSERT-only privileges on these tables — no UPDATE or DELETE ever,
  enforced at the database grant level, not just in application code.
- Corrections are new rows referencing the old one via supersedes_event_id, never edits to history.
- A scheduled job walks and verifies the chain automatically; a manual verify endpoint also exists.
Help me implement this precisely, and flag if anything I ask for would require mutating a past row
or would reintroduce a consensus/multi-writer problem that might actually warrant blockchain instead.
```
