# Frontend integration status

Current frontend behavior is checked against the locally reconciled backend
from `origin/develop` at `6e4ef5c` (PR #11), the trained XGBoost model and the
preserved historical-feature equipment workflow. The companion backend changes remain local and are not part of this frontend-only PR. Team actions are in [FRONTEND-TEAM-HANDOFF.md](FRONTEND-TEAM-HANDOFF.md).

## Latest team branch caveat

The team branch has advanced to `96b4a3f` through PR #13. It now provides audit verification and recorded summary downtime, but still lacks the local monitoring/repair contracts. The notes below describe the tested local companion backend, rather than promising compatibility with untouched `develop`. Reconcile the overview labels, verification helpers, ML input provenance and persisted prediction fields before marking the frontend PR ready.

## Connected surfaces

Paths below begin with `/api/v1`. Tokens remain in an httpOnly cookie. Next.js
validates `/auth/me` and forwards user authorization; FastAPI owns business
rules, station access, model decisions and lifecycle transitions. The internal
ML endpoint is never exposed to browser calls or given a browser service token.

| Surface | Backend connection | Frontend representation |
|---|---|---|
| Session | POST `/auth/login`, GET `/auth/me` | Current demo user-ID identity, actual role/stations, one-hour cookie |
| Operations summary | GET `/dashboard/summary` | Explicitly labels simulated uptime/downtime and backend-wide summary scope; recorded alerts and last-24h incomplete work-order count |
| Equipment workspace | GET `/monitoring/equipment` | Actual backend evaluation states and thresholds; matching-filter empty states; warning state marked unconfigured when the backend warning threshold is null |
| Equipment details | GET `/monitoring/equipment/{id}/history` | Six sensor metrics, recorded sample history, available asset metadata, sensor and ingestion times, probability and saved-threshold decision |
| Prediction evidence | Persisted predictions in monitoring and `/alerts/recent` | Risk level, horizon, target when supplied, model version, prediction ID/time and global model importance when supplied; missing metadata is explicit |
| Maintenance alerts | GET `/alerts/recent` | Triggering snapshot, model context, source station, queue/pipeline status, certification and correlated work order; unavailable order data is not described as an absent task |
| Assignment | GET `/hr/technicians/available`, POST `/maintenance/work-orders`, PATCH `/{id}/assign` | On-shift certified options and active task counts; missing roster/certification prevents unverifiable assignment choices; backend errors are retained |
| Repair lifecycle | PATCH work-order `approve`, `reject`, `escalate`, `start`, `complete` | Controls match current state and engineer/supervisor permissions; completed maintenance does not overwrite risk or claim recovery |
| Lifecycle evidence | GET `/maintenance/work-orders/{id}/lifecycle` | Actors, notes, transitions and recorded hash references; hashes are not presented as verified integrity |
| Equipment downtime | GET `/dashboard/equipment/{id}/downtime` | Recorded dispatch-to-completion windows and open intervals, separate from simulated overview metrics |
| Executive | GET `/dashboard/executive-summary` | Recorded downtime and open/completed/total windows first; scalar indicator labeled as a backend heuristic; savings, dated uptime and comparison only when supplied |
| Operations | GET `/operations/decisions`, `/operations/loading-points` | `/operations` page shows recent automated reroute decisions and loading-bay capacity for engineer, supervisor and executive roles; executive access is read-only |
| Operations details | GET `/operations/decisions/{id}`, `/operations/loading-points/{id}` | Typed client accessors are available for decision action/outcome and bay slot details; the list page does not trigger operational actions |
| Executive equipment access | Same monitoring/history reads | Read-only equipment, alerts and maintenance progress; no assignment or repair controls |
| Audit | GET `/dashboard/audit-logs`, optional `/dashboard/audit-logs/verify` | Latest 50 returned records, filters over that subset, explicit missing/malformed verification; no integrity claim based on loading records |
| Live updates | GET `/events` through `/api/events` | Cookie-authorized SSE, reconnect, committed-event refresh and failure notifications |
| Sample ingestion | POST `/alerts/telemetry` | Legacy sample explicitly described as insufficient for ML; optional station entry, duplicate/queue/evaluation feedback from the actual backend |
| Optional HSE | GET `/hse/overview`, POST `/hse/overfill-risk` | Existing simulated assessment and advisory; no physical equipment commands |

Both API origins and versioned `/api/v1` roots are accepted in the web
`API_BASE_URL`; normalization prevents duplicate path prefixes for auth, reads,
actions and SSE.

## ML semantics

The backend builds its 58 model inputs from six canonical sensor metrics,
asset metadata and 60 earlier complete one-minute readings. The frontend
consumes the persisted evaluation and does not reconstruct features, infer
health from raw temperature/vibration, or replace the saved decision with a
frontend cutoff. The saved threshold is currently 0.12 and the horizon is six
hours; displayed values come from the evaluation or backend configuration.

Default local scoring does not currently attach the service's prediction ID,
timestamp, model-version or importance metadata. The frontend does not invent
those fields. HTTP-mode evaluations retain and display them when returned by
the reconciled ML endpoint. `top_features` is global feature importance,
explicitly separated from explanations of an individual prediction. Lifecycle
hashes belong to the recorded event chain, not to an ML explanation.

Historical probability charts contain only evaluated readings. An unscored
latest reading is called out; missing evaluations are not estimated. A single
threshold line is shown only when all returned evaluated readings share that
threshold. Sensor values use canonical units only when canonical fields were
provided; legacy values retain reported-unit labeling.

## Remaining backend limitations

- `/dashboard/summary` and `/dashboard/audit-logs` still aggregate/list records
  without station filtering. Equipment and work-order reads/actions enforce
  scope, but their protection does not establish station isolation for the
  global summary or audit list. This requires backend work.
- Summary uptime and downtime use simulated formulas. Executive/equipment
  downtime endpoints use persisted windows; neither proves avoided downtime
  or savings. Executive `uptime_trend` is currently a heuristic string.
- `/dashboard/audit-logs/verify` is not mounted by the active backend. Missing
  or malformed verification remains unavailable, distinct from failed checks.
- Schema migration adds columns and app-role grants but preserves existing
  unchained audit rows. The local legacy-tail ingestion blocker remains until a
  separately reviewed history migration is implemented.
- PostgreSQL role-grant enforcement requires a live PostgreSQL validation run;
  SQLite does not establish that enforcement.
- Demo identity is not production authentication. The demo technician identity
  is not linked to the HR assignment IDs, so adding a technician web execution
  flow would require that backend identity mapping first.
- HR/inventory and HSE remain simulated sources. SMS delivery, broader
  multi-worker SSE and mobile/offline integrations remain outside this frontend
  reconciliation. Loading-point reassignment is internal-service-only; the
  frontend reads its persisted decision, action and outcome records but cannot
  trigger a reroute.

## Verification

- `npm run lint`, `npm run typecheck`, `npm run build`.
- `npm run test:smoke` checks production rendering against fixture contracts,
  cookie auth/actions, role guards, backend errors, filters, ML metadata, absent
  or malformed audit verification, SSE and current/optional executive shapes.
- `npm run test:backend` starts the actual FastAPI application and trained model
  with an isolated in-memory database and a production Next.js server. It checks
  real HTTP ML scoring, rendered probability/version/ID, alert-based certified
  assignment, approval/start/completion, downtime, executive read-only equipment
  access, and accurate summary/audit states. Only broker dispatch is replaced;
  model inference, API authorization, persistence and lifecycle handlers are
  real. No live application database is used. This test requires Python and the
  root backend dependencies; `PYTHON` can select the interpreter.
- Current backend suite: 67 passed, one PostgreSQL-grants test skipped without
  `TEST_ADMIN_DATABASE_URL`. The older 43-pass/2-failure telemetry mismatch and
  48-check equipment-review results are historical, not current validation.

No full Docker stack or live production data migration has been performed.
