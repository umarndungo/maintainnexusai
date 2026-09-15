# Disabled

This app is disabled. It's an older Flutter dashboard, superseded by:

- **`technician-mobile-app/`** — the maintained Flutter mobile client (offline-first, matches the
  Mobile & Web Experience Spec).
- **`web/`** — the Next.js web dashboard, for engineer/supervisor/executive workspaces.

Its `ws_service.dart` also connects to a raw WebSocket route the backend no longer exposes — live
updates now go over SSE (`GET /api/v1/events`, see `web/src/components/live-updates.tsx` for a
working consumer), which this app never adopted.

Kept on disk (not deleted) in case anything here is worth salvaging later. Not part of any build,
CI, or docker-compose workflow.
