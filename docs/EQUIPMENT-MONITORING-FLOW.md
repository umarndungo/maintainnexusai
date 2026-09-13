# Equipment monitoring and maintenance integration

## Review before implementation

The Next.js dashboard fetched `/dashboard/summary`, `/alerts/recent`, and
`/maintenance/work-orders` on the server with the cookie session token. Health
cards showed up to five audit-derived telemetry checks. Equipment details only
showed downtime and maintenance history. No sensor history, assignment form, or
start/completion controls existed. The existing SSE subscriber refreshed pages,
but ingestion did not publish events and lifecycle events omitted station IDs.

The FastAPI alert gateway already persisted alerts and invoked Celery. The ETL
pipeline checked stock, mapped failure codes to certifications, selected an
on-shift technician, and created an assigned work order awaiting approval.
Approval dispatched it; the lifecycle transition helper already understood
`IN_PROGRESS` and `COMPLETED`, although no public routes invoked those states.
The warehouse and HR APIs already use in-memory simulated sources. They have
been reused, not replaced with new mock services.

The new XGBoost scorer returns a structured prediction and requires 58 features.
Its saved threshold is 0.12, with a six-hour prediction horizon. Legacy ingestion
and Beat code incorrectly expected a numeric score from three sensor fields,
and applied an unrelated 0.85 threshold. Temperature/vibration constants in the
legacy alert builder choose a failure code; they are not independent configured
sensor failure limits. No near-threshold configuration was available.

## Implemented architecture

The new `/equipment` workspace and expanded `/equipment/{id}` pages read the
FastAPI monitoring projection. The dashboard links into this workflow and shows
equipment requiring attention. Shared components render equipment states, metric
cards, timestamp-based SVG trends, detailed alerts, and maintenance controls.
Work-order details also expose the same controls to engineers and supervisors;
executive users remain read-only.

All risk evaluation, certification mapping, assignment validation, status
transitions and persistence remain in Python. Next.js route handlers only attach
the httpOnly cookie token and forward the request. No production mock API,
offline fallback, localStorage business state, or frontend threshold evaluator
has been added.

## API contracts

All paths below start with `/api/v1`.

| Endpoint | Behavior |
|---|---|
| GET `/monitoring/equipment` | Latest persisted sensor reading per accessible asset, server state, prediction, thresholds and source |
| GET `/monitoring/equipment/{id}/history?limit=200` | Chronological recorded readings and evaluations; limit 1–500 |
| POST `/alerts/telemetry` | Existing raw fields plus optional canonical sensor/asset fields; persist validated reading, evaluate compatible input, generate and queue server alert |
| GET `/alerts/recent` | Existing alert fields plus telemetry snapshot, structured prediction, required certification and available pipeline outcome |
| GET `/hr/technicians/available` | Existing on-shift roster with certification data and active task counts from persisted work orders |
| POST `/maintenance/work-orders` | Existing create body; interactive calls require a real `alert_task_id`, matching asset/part, available stock and certified technician |
| PATCH `/maintenance/work-orders/{id}/assign` | `{ "technician_id": "..." }`; validate roster, shift, certification, stock and allowed state; append assignment history |
| PATCH `/maintenance/work-orders/{id}/approve` | Existing operation; approve then dispatch |
| PATCH `/maintenance/work-orders/{id}/reject` | Existing rejection; does not clear equipment failure risk |
| PATCH `/maintenance/work-orders/{id}/escalate` | Existing supervisor operation; also accepts authenticated internal scheduler calls |
| PATCH `/maintenance/work-orders/{id}/start` | Dispatched → in progress |
| PATCH `/maintenance/work-orders/{id}/complete` | In progress → completed; close downtime window |
| GET `/maintenance/work-orders/{id}/lifecycle` | Append-only handoff and transition history |
| GET `/dashboard/equipment/{id}/downtime` | Real dispatch-to-completion intervals, with UTC-normalized durations |
| GET `/events` | Push `telemetry.received`, `alert.created`, and `work_order.lifecycle` after committed changes |

Interactive writes require engineer/supervisor authorization. Technician
start/completion requires assignment to that technician's authenticated ID.
The existing demo technician login is not mapped to the separate HR technician
IDs, so engineer/supervisor controls are the usable web execution path.

New ingestion requires a station owner. A user assigned to exactly one station
may omit `station_id`; internal services and cross-station users must supply it.
An existing asset cannot silently move between stations. Engineers cannot read
or act on assets outside their stations. Legacy unknown-ownership events remain
preserved and visible to cross-station roles; they are not assigned to an
engineer's station by assumption.

## Sensor ingestion and evaluation

The existing mandatory ingestion fields remain `equipment_id`, `temperature`,
`vibration`, `installation_age_hours`, and timezone-aware `timestamp`.
Full model-compatible streams additionally supply `asset_id` (matching equipment
ID), `asset_type`, `operating_state`, `alarm_code`, and the canonical metrics
`pressure_bar`, `temperature_c`, `flow_rate_m3h`, `motor_current_a`,
`vibration_mm_s`, and `valve_position_pct`. Legacy temperature/vibration aliases
must agree with canonical values when both are supplied. Canonical values must
be finite and nonnegative, with valve position between 0 and 100.

`ml/live_features.py` uses the training feature builder's sensor names and
5/15/60-reading windows. It computes lag, delta, historical mean and standard
deviation from earlier readings for the same asset/station. It requires 60
complete preceding readings at the training dataset's one-minute cadence and
supported categorical values. No future input, zero-filled sensors, fake
history, or legacy heuristic is substituted. Incomplete streams are persisted
as `UNSCORED`, with an explanation, and do not create model-driven alerts.

Successful evaluation preserves the scorer's probability, predicted-failure
flag, risk level, threshold and horizon. The projection renders:

- `FAILURE_DETECTED` when the scorer predicts failure.
- `APPROACHING_THRESHOLD` below failure when an optional backend warning
  probability is explicitly configured and exceeded.
- `NORMAL` for a compatible evaluation below configured limits.
- `UNSCORED` when a compatible evaluation is absent, including legacy readings.

`RISK_WARNING_THRESHOLD` is optional and must be below the model threshold.
Unset means no approaching-threshold band exists. It is not invented in the UI.
Per-sensor failure limits are not exposed by the current model; the UI says so
and marks the probability threshold, not imaginary temperature/vibration limits.

The Beat simulator now uses the same HTTP ingestion gateway. It is enabled only
with explicit `SIMULATED_STATION_ID`; its existing three-field samples remain
unscored. The SLA scheduler also uses the existing escalation gateway so changes
publish SSE. Internal HR/warehouse lookups now carry the existing service token.

## Failure-to-recovery flow

1. A validated reading is persisted and pushed to monitoring clients.
2. Complete input is scored against the saved backend threshold.
3. Predicted failure creates a persisted alert with the triggering snapshot.
4. Celery checks stock and technician eligibility and creates assigned maintenance.
   Missing broker, pipeline hold, or external-source states remain explicit.
5. If no task is returned, an engineer/supervisor can create and assign one from
   the actual alert. Concurrent source-alert creation is serialized in PostgreSQL,
   and existing correlated tasks return 409 instead of a second task.
6. The reviewer may change the eligible assignment, then approve and dispatch.
7. Start and completion advance the persisted lifecycle and refresh the UI.
8. Completion closes the downtime window. A fresh evaluated reading establishes
   current risk; completion alone never resets equipment health or erases alerts.

Metric cards and charts show sensor time separately from ingestion time.
Historical alert snapshots are retained even when the latest equipment risk
returns to normal. SSE refreshes committed data and displays a failure
notification; reconnect readiness reloads missed changes. There is no polling.

## Current limitations and validation

- The current local `maintainnexus.db` contains four legacy audit rows without
  hashes. The inherited append-only writer deliberately rejects appending to
  such history. Ingestion returns an actionable 503; a reviewed database
  migration is required. Existing rows are preserved.
- Real sensor streams must provide the model input described above. The legacy
  sample generator cannot demonstrate trained-model threshold detection.
- HR/inventory remain the existing simulated backend sources, not production
  workforce/warehouse integrations. SMS gateway provider delivery is still a
  separate backend integration.
- SSE subscribers are process-local. Current single-worker API deployment works
  because scheduled ingestion/escalation and worker work-order creation use its
  HTTP gateways. Multi-worker SSE needs a shared event bus.
- Existing executive savings/audit verification and station master-data gaps are
  outside this equipment workflow and remain documented in the integration status.

Validation includes the actual FastAPI routes, SQLAlchemy persistence and
append-only lifecycle against an isolated database, with the broker/scorer
substituted only in tests to force failure/recovery scenarios. Real trained-model
inference is also checked against the live feature schema. Frontend production
smoke fixtures exercise rendered metrics, alert context, charts, assignment and
role-restricted proxy calls. Fixtures are not application data sources.
