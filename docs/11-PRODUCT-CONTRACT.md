# Product contract — Predict → Decide → Act → Learn

**Status:** Frozen for MVP  
**Date:** 2026-09-12  
**Scope:** Depot loading arms, pumps, and valves only.

This is the one-page product freeze. Architecture, ETL, ML, and UI work must match it. Do not expand into transformers, leak detection, SCADA cybersecurity, or physical pump/valve control.

## Objective

Turn a failure-risk prediction into an **idempotent operational action** that keeps loading moving, then record whether the prediction and the action were right.

Not: a dashboard that only tells a manager a truck will be delayed.  
Not: the model commanding safety-critical equipment.

## Closed loop

```
telemetry event
        → feature snapshot
        → POST /api/v1/ml/predict-risk
        → decision engine (rules + inventory + alternate bay)
        → action API
        → operational outcome
        → feedback event
```

## Predict (ML)

| Item | MVP value |
|---|---|
| Assets | `PUMP`, `LOADING_ARM`, `VALVE` |
| Target | `failure_within_24h ∈ {0,1}` |
| Output | `risk_score` 0–1, `risk_level`, `prediction_horizon_hours=24`, `top_features`, `prediction_id`, `model_version` |
| Must not | Query Postgres, reschedule trucks, start/stop equipment |

Horizon 7d / 90d and remaining-useful-life are follow-ons.

## Decide (backend, not the model)

The decision engine may act only if **all** are true:

1. `risk_level` meets the policy threshold for that `equipment_type` and `criticality`.
2. The asset is tied to an active loading point / slot.
3. A compatible alternate loading point has capacity (or the slot can be marked unavailable).
4. The action is in the allowed set below.
5. The request is idempotent (`idempotency_key`).

If spare stock is zero, still allow **reassignment** (protect throughput) and open a work order / spare alert. Do not block reroute on missing parts.

## Act (MVP: one primary API)

**Primary action:** reassign the affected truck to another loading point.

`POST /api/v1/operations/loading-points/reassign`

Payload matches `schemas/operational-action-request.schema.json`:

- `action_type`: `REASSIGN_LOADING_POINT` (primary)
- also allowed: `RESCHEDULE_TRUCK`, `CREATE_MAINTENANCE_WORK_ORDER`
- required: `action_id`, `decision_id`, `idempotency_key`, `requested_at`

**Out of scope for autonomous action:** start/stop pumps, open/close valves, change refinery batch. Those may be *simulated* as logged “would-require-interlock” events only.

## Observe / learn

Every action writes `OPERATIONAL_ACTION_OUTCOME` with:

- `prediction_id`, `action_id`, `action_success`
- `actual_failure` (when known)
- `actual_delay_minutes`
- whether an alternate bay completed the load

Training data never mixes with live inference except through an explicit reviewed export (`docs/09-DATA-REQUIREMENTS-MATRIX.md`).

## Golden-path demo (must run without a human click)

1. Synthetic PS25 loading-pump telemetry degrades (vibration + bearing temperature).
2. Risk exceeds threshold for a critical pump.
3. Decision engine marks the bay unavailable and reassigns the next truck.
4. Work order is created at `PENDING_APPROVAL` (engineer still gates physical repair).
5. Spare check is logged (even if stock is zero).
6. Outcome is stored.

## Provenance rule

Public KPC tenders and reports justify **which equipment and failure modes exist**.  
They do **not** provide live SCADA. Any time series used in the prototype is **synthetic, KPC-spec-aligned**, and must be labelled as such.

Equipment inventory: `data/kpc_public/`.
