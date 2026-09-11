# Data / ML Implementation Guide

**Owner:** ML track owner
**Reads:** `00-PROJECT-DOC.md` §6 before starting.

---

## 1. Scope

Turn the current inline/placeholder risk scoring into an actual model behind a stable API contract,
trained on historical data, validated, and callable by the backend's ETL pipeline without the pipeline
needing to know anything about the model's internals.

## 2. The two data paths — keep them separate, always

| Path | Source | Used for | Touches live pipeline? |
|---|---|---|---|
| Live/production | Real or simulated sensor telemetry via `/alerts/telemetry` + Celery Beat generator | Scoring in production | Yes — this *is* the pipeline |
| Historical/training | Kaggle-style equipment-failure datasets, scraped web data | Training + validating the model offline | **No** — separate storage, separate job, never mixed into live tables |

If you need to backfill or augment training data from production history later, do it as an explicit,
reviewed export step — never point the training job directly at the live Postgres tables. This
applies doubly to `work_order_lifecycle_events` and `audit_logs`, which are hash-chained and
insert-only (`07-AUDITING-GUIDE.md`) — an export job reads from them, it never writes to or through them.

## 3. Model contract (what backend calls)

`POST /api/v1/ml/predict-risk`

Request: sensor readings (temp, pressure, vibration) + equipment metadata (location, station, type,
equipment age/last-service-date).

Response must include:
- `risk_score` (0–1 or equivalent)
- `risk_level` (derived bucket: low/medium/high — backend/frontend shouldn't have to reimplement
  the threshold logic)
- `top_features` — ranked list of which inputs drove the score (e.g. `["vibration: 3.2x baseline",
  "pressure trending up over 6hrs"]`), in plain enough form that the frontend's risk-driver display
  can render it directly without translation

This response shape is a contract with both Backend and Frontend guides — changing field names means
updating those docs too, not just your model code.

## 4. Pipeline placement

You are the "Score valid telemetry for equipment failure risk" step in the 7-step ETL flow (project
doc §6, step 3). Backend owns steps before and after you (validation, dispatch); you own only the
scoring call itself. Keep the model served as its own process/service (even if co-located in the same
repo initially) so it can be retrained/redeployed without redeploying the whole API.

## 5. Tasks

- Source and clean a historical failure dataset (Kaggle or equivalent) for loading-arm/pump/valve-type
  equipment — document the source and license.
- Feature engineering: rolling windows on vibration/pressure/temp, equipment age, time-since-last-service.
- Train a baseline model (start simple — gradient-boosted trees or logistic regression with the
  engineered features — before reaching for anything heavier; explainability matters here because the
  engineer view needs the "why").
- Validate against held-out historical data; report precision/recall on the failure class specifically,
  not just accuracy (false negatives here mean missed failures — weight that in your evaluation).
- Wrap the trained model behind the `/predict-risk` contract above.
- Define the risk-level thresholds (low/medium/high) in one place, document them, and give backend
  the exact threshold above which a work order should be auto-created — this is a product decision
  as much as a technical one, confirm it with the team rather than picking unilaterally.

## 6. AI context block

```
I'm building the ML risk-scoring component for MaintainNexus, a predictive-maintenance system for
loading arms, pumps, and valves. My job is a model behind POST /api/v1/ml/predict-risk that takes
sensor telemetry + equipment metadata and returns a risk_score, a risk_level bucket, and a ranked
list of top contributing features in plain-language form (for a non-ML engineer-facing UI).

Hard constraints:
- Training data (historical/Kaggle-style) and live production telemetry are separate paths that
  never mix. I don't train on live pipeline data without an explicit, reviewed export step.
- The model's output field names are a contract with the backend and frontend teams — I don't
  rename or restructure them without updating the shared project doc.
- Explainability matters as much as accuracy: the top_features output is what an engineer sees to
  decide whether to approve a work order, so prefer models/features that support that over pure
  black-box accuracy gains.
- Evaluate on precision/recall for the failure class, not just overall accuracy — missed failures
  (false negatives) are the costly error here.
Help me build and validate this model against that contract.
```
