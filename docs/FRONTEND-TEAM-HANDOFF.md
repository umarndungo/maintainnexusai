# Frontend team handoff

This frontend-only pull request targets `develop`. The previously published
frontend commit `8088c5b` is already in `develop` through PR #12. The changes
here add prediction evidence, clearer data/error states, read-only executive
monitoring, safer assignment choices and integration checks. They do not
include the local backend/database reconciliation.

The latest team baseline checked is `96b4a3f`, including
[PR #13](https://github.com/umarndungo/maintainnexusai/pull/13). Keep its useful
backend fixes; reconcile the differences below before merging this draft or
presenting the full workflow as integrated.

## Required team work

1. **Backend/integrations: publish the monitoring and repair contracts.**
   The local candidate implements `GET /api/v1/monitoring/equipment`,
   `GET /api/v1/monitoring/equipment/{id}/history`, and PATCH work-order
   `assign`, `start` and `complete`. The current team branch lacks these
   routes. The frontend needs persisted readings, station ownership,
   backend evaluation states, thresholds, source/evaluation reasons and
   correlated alerts/work orders. Preserve station authorization, real
   technician certification/shift checks, recorded downtime and publication
   of SSE only after commit. Backend code for this is still local and must
   be reviewed/shared separately.

2. **ML and backend: agree one prediction contract without losing provenance.**
   The candidate uses real sensor metadata, six canonical metrics and 60
   earlier complete one-minute readings. PR #13 also adds history-based
   feature engineering, but fills missing sensors with neutral values and
   maps equipment IDs to trained buckets. Review that difference explicitly;
   do not treat inferred/defaulted inputs as observed sensor data or replace
   real recorded history silently. Preserve the trained threshold and expose
   `failure_probability`, `failure_predicted`, `threshold`, `risk_level`,
   `prediction_horizon_hours`, and `target` in persisted evaluations. Retain
   service `model_version`, `prediction_id`, timestamp and `top_features`
   when supplied. `risk_score` may be a compatibility alias. The current
   team ML endpoint does not return the complete candidate contract, and its
   high-risk label may differ. Global importance must stay separate from
   explanations of an individual prediction. Missing compatible input should
   have an explicit evaluation/provenance state.

3. **Frontend and backend: reconcile the overview with PR #13.**
   The current frontend candidate labels the older local summary's simulated
   uptime/downtime accurately. PR #13 now derives summary downtime from
   persisted `DowntimeWindow` records; update that label for the deployed
   backend, ideally using a backend-provided provenance field. Its uptime
   percentage remains a clamped calculation and should not be presented as
   directly measured equipment availability. Keep summary/audit global scope
   explicit until those routes enforce station isolation. Do not relabel
   accumulated downtime as avoided downtime or cost savings.

4. **Backend/audit: retain and validate the new verification endpoint.**
   PR #13 implements `/api/v1/dashboard/audit-logs/verify` with
   `chain_integrity`, `checked_events`, `chain`, and `verified_at`; the frontend
   is ready to render that shape and treats missing/malformed results as
   unavailable. The local backend candidate used for the earlier integration
   check does not yet include this new endpoint. Preserve stored audit/lifecycle
   timestamps and hash semantics when bringing in the verification helpers.
   Schema-column migration alone does not repair unchained legacy data.

5. **Database/deployment: apply and verify the restricted role setup.**
   Keep the team's migration service, app/admin role separation and PR #13's
   PostgreSQL data volume. Use existing working admin credentials and run
   migrations before API/workers. Verify SELECT/INSERT on audit/lifecycle
   tables, denied UPDATE/DELETE (and no TRUNCATE privilege), and normal
   operational-table CRUD against a live PostgreSQL server. Resolve the
   existing legacy audit-tail ingestion blocker with a separately reviewed
   history migration. Never delete history to make the demo run.

6. **Everyone: validate the combined branch before marking the PR ready.**
   Run the frontend checks below after reconciling the companion backend.
   Exercise reading → prediction → alert → certified assignment → approval
   → dispatch → start → completion → fresh reading. Completing maintenance
   must not overwrite the last model evaluation or imply recovery. Test
   engineer/supervisor operations access, executive read-only operations access,
   technician denial, queue outages, unsupported inputs, duplicate timestamps
   and real audit verification.

## Frontend checks and limits

```powershell
cd web
npm.cmd run lint
npm.cmd run build
npm.cmd run typecheck
npm.cmd run test:smoke
npm.cmd run test:backend
```

The first four checks passed for this frontend. `test:smoke` uses test-only
fixtures and does not establish live backend compatibility.

`test:backend` also passed against the **local companion backend candidate**
with the actual FastAPI handlers and trained model, an isolated in-memory
SQLite database, and Celery broker dispatch replaced in the test. It verifies
rendered ML evidence and the repair lifecycle. It requires the pending
monitoring/lifecycle contracts; it is not expected to pass against untouched
`develop` yet. Python plus the root backend dependencies are required; `PYTHON`
can select an interpreter. The test does not use the live application database.

The local companion backend suite passed 67 tests. Its PostgreSQL permissions
check was skipped without a live server. These results do not claim that the
latest PR #13 backend has been reconciled or validated with this frontend.

No production database migration or full Docker stack run was performed.
The detailed frontend-to-backend field mapping is in
[FRONTEND-INTEGRATION-STATUS.md](FRONTEND-INTEGRATION-STATUS.md).
