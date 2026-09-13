> Equipment workflow update: see [EQUIPMENT-MONITORING-FLOW.md](EQUIPMENT-MONITORING-FLOW.md).
> The telemetry scoring return-contract mismatch is now repaired. Complete canonical
> streams use historical features; incomplete legacy streams remain unscored.
> Monitoring/history and assignment/start/completion routes are implemented, with
> station-scoped equipment/work-order access and committed SSE publication.
> The previous 43/2 test result below is historical; the expanded backend suite
> currently passes 48 checks. Legacy audit migration remains a local ingestion blocker.

# Frontend integration status

Reviewed against the team updates merged from `origin/develop` at `88efe6d` on 2026-09-13. This records implementation and handoff gaps; it does not replace the shared API or frozen product contracts.

## Connected surfaces

All paths below begin with `/api/v1`. Tokens remain in a server-set httpOnly cookie. Protected page loads validate `/auth/me`; mutations validate the role before forwarding and still rely on FastAPI for business authorization and transitions.

| Surface | Connection | State |
|---|---|---|
| Login/session | POST `/auth/login`, GET `/auth/me` | Uses current `user_id` login, confirmed role/stations, one-hour cookie; no refresh endpoint invented |
| Engineer/supervisor overview | GET `/dashboard/summary` | Metrics, equipment health, available technicians, inventory |
| Work-order queue | GET `/maintenance/work-orders` | Status filters, approval/rejection, links and lifecycle drawer |
| Supervisor queue | Same list plus PATCH `/{id}/escalate` | Escalated queue, approve/reject escalated orders, manual escalation of pending orders |
| Recent alerts | GET `/alerts/recent` | Alert feed linked to equipment |
| Lifecycle | GET `/maintenance/work-orders/{id}/lifecycle` | Drawer and persisted history page; renders risk explanations only when supplied |
| Equipment | GET `/dashboard/equipment/{id}/downtime` plus work-order list | Downtime windows and maintenance history links |
| Executive | GET `/dashboard/executive-summary` | Current tracked downtime and trend bucket; preserves planned avoided downtime, savings, dated trend/chart and station comparison fields |
| Audit | GET `/dashboard/audit-logs`, GET `/dashboard/audit-logs/verify` | Read-only records with event/date filters; missing verification is explicitly unavailable, separate from failure |
| Live updates | GET `/events` through Next.js `/api/events` | SSE confirmed by backend guide; cookie authentication, native reconnect, push-triggered refresh, no polling |
| Presentation controls | POST `/alerts/telemetry`, POST `/maintenance/work-orders` | Preserved; use real backend responses, not frontend business logic |
| Optional HSE extension | GET `/hse/overview`, POST `/hse/overfill-risk` | Preserved simulated tank snapshot/advisory API; uses merged auth boundary; no physical equipment commands |

## Backend/ML handoff requirements

- Station isolation is not yet established by the imported backend. Work orders/equipment lack station ownership fields, several GET routes return all records, and emitted lifecycle events do not yet carry station ownership. SSE subscriptions now restrict engineers/technicians to their permitted stations; unknown-station events are not sent to them. Backend owners must attach the actual station to lifecycle/alert events to enable station-user updates. Web role guards and displaying `/auth/me` stations do not fix this. Backend owners must enforce station ownership on reads, actions, and streams; the client does not invent a station mapping or filter unscoped records as a substitute.
- `/dashboard/audit-logs/verify` remains a documented follow-up. Keep the frontend connection; do not infer integrity from successful data loading. Backend scheduled verification and DB grant enforcement require their own validation.
- Executive summary currently supplies `downtime_minutes`, window counts, and a string `uptime_trend`. It does not yet supply `downtime_avoided_minutes`, `cost_saved`, dated uptime points, or station comparison. The frontend supports both the current response and its previously implemented planned shape without relabelling tracked downtime as avoided downtime.
- Work-order and lifecycle responses do not supply the frontend's existing `risk_drivers`/`top_features` explanations. Agree and document exact fields with backend/ML owners; no explanations are fabricated.
- The merged ML scorer requires 58 engineered features and returns a dictionary. Existing `etl/telemetry.py` and `tasks.py` callers still supply the legacy raw telemetry shape and compare the return value as a number. Backend/ML must adapt feature generation and consume the saved model threshold; do not restore the old heuristic or zero-fill unavailable features. XGBoost and its scikit-learn wrapper dependency are now declared in `requirements.txt`.
- The frozen product contract describes a 24-hour horizon while the latest ML handoff describes a 6-hour model. Owners must reconcile the documents. No prediction horizon or decision policy is invented in the frontend.
- Loading-point reassignment, autonomous decision/outcome handling, SMS provider delivery, and offline mobile remain separate team-owned integrations. The web never calls internal ML/SMS routes or commands equipment.
- The backend only offers demo user-ID authentication. Password credentials, refresh tokens, and production identity management remain backend/integrations work.
- HSE is explicitly preserved at the user's request as an optional simulated presentation extension. It is not a claim that the frozen automation MVP has expanded to live spill detection or equipment control.

## Deployment and verification

`web/Dockerfile` builds the documented standalone server; Compose now includes the web service and its health check. `web/.env.example` documents the server-side API origin. Frontend CI runs lint, build, typecheck and the test-only mocked integration smoke suite on PRs. Production secret/CORS policies, backend CI, ML service health checks and mobile release validation remain deployment-owner work.


## Validation for this change

- Frontend lint, production build and TypeScript checks pass.
- Production-server smoke checks pass against the test-only API: login/identity, httpOnly cookie, forbidden roles, expired/unavailable sessions, status filtering, cookie-only mutations, supervisor escalation, lifecycle proxy, verification unavailable, SSE and both executive response shapes.
- Eight focused backend/auth/lifecycle/SSE tests pass. Full backend suite: 43 pass, 2 fail in the inherited raw-telemetry/model-feature mismatch described above (`TestProcessRawTelemetry`). This is not a passing end-to-end ML ingestion pipeline.
- API import succeeds after installing XGBoost/scikit-learn. Compose configuration validates; a full Docker image/stack run and live database/station-isolation validation have not been performed.
