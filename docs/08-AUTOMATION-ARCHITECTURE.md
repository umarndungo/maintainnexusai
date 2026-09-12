# MaintainNexus Repository Gap Audit — Predict → Decide → Act → Learn

**Date:** 2026-09-12

## What already exists
- FastAPI backend, Celery/Redis, PostgreSQL/SQLAlchemy.
- Telemetry validation and synthetic telemetry generation.
- ETL flow from telemetry/alert to stock/technician/work order.
- Prometheus metrics and CI.
- Existing documentation already scopes loading arms, pumps and valves.

## Critical gaps

| Gap | Current state | Required upgrade | Owner |
|---|---|---|---|
| Real ML model | `ml/scoring.py` is a mathematical placeholder | Offline training, evaluation, artifact/versioning, inference service | ML |
| ML API | `/api/v1/ml/predict-risk` is documented, not implemented as a real model service | Stable prediction API | ML + Backend |
| Equipment taxonomy | Mostly pumps plus generic assets | Canonical `PUMP`, `LOADING_ARM`, `VALVE` taxonomy | ML + Backend |
| Telemetry | Only temperature, vibration, age | Equipment-specific telemetry schema | ML + Data |
| Training data | No separated training dataset path | Offline training storage + provenance | ML + Data |
| Failure labels | No failure-event schema | `failure_within_24h` baseline target | ML |
| Operational context | No truck/loading-point scheduling model | Trucks, loading points, slots, capacity, compatibility | Backend |
| Automated action | Work-order dispatch only | Decision engine + reschedule/reassign/action APIs | Backend |
| Event architecture | Celery exists, but no domain event contracts | Prediction/decision/action events + idempotency | Backend + DevOps |
| Feedback | No prediction/action/outcome chain | Outcome schema + monitoring/retraining path | ML + Backend |
| Frontend | Legacy Flutter UI | Next.js dashboard migration; keep legacy until migration works | Frontend |
| Lifecycle/audit | Docs specify event sourcing/hash chains, models still contain mutable `status` and no lifecycle table | Implement documented lifecycle/audit design | Backend |
| Inventory | Random in-memory values | Persistent/contracted inventory source | Backend/Data |
| Safety boundary | No explicit automation policy | Separate safe operational automation from physical control | Product + Backend |

## Priority
**P0:** shared contracts/data requirements → **P1:** ML model/API + operational decision/action APIs → **P2:** Kafka/event hardening, observability, deployment and feedback.

## Do not do yet
- Do not call synthetic telemetry real KPC telemetry.
- Do not let ML directly control safety-critical pumps/valves.
- Do not delete the Flutter directory until Next.js migration is working.
- Do not choose a complex model before the target/data are defined.
- Do not let ML bypass backend contracts by querying operational databases directly.
