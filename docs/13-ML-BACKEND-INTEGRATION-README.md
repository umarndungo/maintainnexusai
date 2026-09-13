# MaintainNexusAI — ML Backend Integration Guide

## 1. Purpose

This document defines how the MaintainNexusAI backend should integrate with the finalized predictive-maintenance machine-learning pipeline.

The ML component predicts whether an equipment asset is likely to experience a failure **within the next 6 hours**, based on recent telemetry and operational conditions.

The backend's responsibility is to:

1. Collect or receive equipment telemetry.
2. Prepare the model-compatible feature payload.
3. Call the ML scorer.
4. Store or expose the prediction result.
5. Apply application-level alert and maintenance workflows based on the prediction.
6. Return prediction information to the frontend where required.

The backend **must not retrain the model** or independently redefine the model's prediction threshold.

---

# 2. Current ML Model

## 2.1 Model

| Property                 | Value                                                     |
| ------------------------ | --------------------------------------------------------- |
| Model                    | XGBoost                                                   |
| XGBoost version          | 3.4.1                                                     |
| Problem                  | Binary classification                                     |
| Target                   | `failure_next_6h`                                         |
| Prediction horizon       | 6 hours                                                   |
| Number of model features | 58                                                        |
| Categorical features     | `asset_id`, `asset_type`, `operating_state`, `alarm_code` |
| Decision threshold       | `0.12`                                                    |
| Random state             | 42                                                        |
| Model artifact           | `ml/models/maintainnexus_xgboost.json`                    |
| Metadata artifact        | `ml/models/model_metadata.json`                           |

The model predicts:

> "Is this asset expected to experience a failure within the next 6 hours?"

It does **not** predict the exact failure time.

---

# 3. Model Performance

The model was evaluated using a chronological train/validation/test split.

The final threshold was selected using the validation dataset and then applied unchanged to the test dataset.

## 3.1 Test performance

| Metric    | Result |
| --------- | -----: |
| Precision | 94.16% |
| Recall    | 52.05% |
| F1 Score  | 67.04% |
| ROC-AUC   | 76.55% |
| PR-AUC    | 55.35% |

Test confusion matrix:

```text
                    Predicted
                  Negative Positive
Actual Negative    305351      166
Actual Positive      2464     2675
```

This means the final test set contained:

* 5,139 actual positive failure-window observations.
* 305,517 actual negative observations.
* 2,675 positive observations correctly detected.
* 2,464 positive observations missed.
* 166 false positives.

The model therefore provides a **risk signal**, not a guarantee that an asset will fail.

---

# 4. ML Repository Structure

The important ML components are:

```text
ml/
├── models/
│   ├── maintainnexus_xgboost.json
│   ├── model_metadata.json
│   └── feature_importance.csv
│
├── src/
│   └── targets/
│       └── build_failure_target.py
│
├── scoring.py
└── train_xgboost.py

src/
├── features/
│   └── build_features.py
└── split_data.py
```

The backend integration should use:

```text
ml/scoring.py
```

and the saved model:

```text
ml/models/maintainnexus_xgboost.json
```

The backend should **not implement a second copy of the XGBoost prediction logic**.

---

# 5. Scoring Interface

The production scorer exposes:

```python
from ml.scoring import score_telemetry
```

The backend calls:

```python
result = score_telemetry(feature_payload)
```

The function accepts a dictionary containing the required model features.

Example:

```python
result = score_telemetry(payload)
```

The scorer:

1. Converts the payload into a pandas DataFrame.
2. Validates that all required model features exist.
3. Selects only the 58 model features.
4. Restores categorical feature types.
5. Runs the saved XGBoost model.
6. Produces a failure probability.
7. Applies the saved threshold.
8. Assigns a risk level.

---

# 6. Critical Input Requirement

## The scorer does NOT accept raw telemetry alone.

The model was trained using **58 engineered features**.

Therefore, the following is **not sufficient**:

```json
{
  "pressure_bar": 4.2,
  "temperature_c": 65.4,
  "flow_rate_m3h": 120.5,
  "motor_current_a": 15.1,
  "vibration_mm_s": 8.3,
  "valve_position_pct": 72
}
```

Those are only the raw sensor measurements.

The backend must provide the feature-engineered representation expected by the model.

---

# 7. Feature Engineering Contract

The feature engineering pipeline was built from telemetry grouped by asset.

The original telemetry sampling interval is:

```text
1 minute
```

The model uses the following raw sensor fields:

```text
pressure_bar
temperature_c
flow_rate_m3h
motor_current_a
vibration_mm_s
valve_position_pct
```

For each sensor, the feature pipeline generates:

* Current value
* Lag-1 value
* Delta-1 value
* Rolling mean over 5 minutes
* Rolling standard deviation over 5 minutes
* Rolling mean over 15 minutes
* Rolling standard deviation over 15 minutes
* Rolling mean over 60 minutes
* Rolling standard deviation over 60 minutes

The pipeline also includes categorical/operational features:

```text
asset_id
asset_type
operating_state
alarm_code
```

The original calendar fields were generated during feature engineering but were **excluded from the final model** because they introduced an undesirable synthetic-calendar dependency:

```text
hour
day_of_week
month
is_weekend
```

These fields must therefore **not** be sent to the final scorer.

---

# 8. Leakage Fields

The following fields were used during target construction or data processing and must not be supplied as model features:

```text
failure_flag
failure_type
failure_event_start
next_failure_timestamp
hours_to_failure
provenance
```

In particular, the backend must never send information such as:

```text
failure_event_start
next_failure_timestamp
hours_to_failure
```

to the production scorer.

Those fields would expose information that would not be available at prediction time.

---

# 9. Model Feature Set

The exact authoritative list of features is stored in:

```text
ml/models/model_metadata.json
```

The metadata file contains:

```text
target
threshold
features
categorical_features
categorical_values
excluded_features
```

The backend integration should treat `model_metadata.json` as the source of truth for the exact feature names.

Do not manually rename model features.

Do not silently substitute similar field names.

For example:

```text
temperature
```

is not equivalent to:

```text
temperature_c
```

and:

```text
vibration
```

is not equivalent to:

```text
vibration_mm_s
```

---

# 10. Feature Preparation Architecture

The recommended backend architecture is:

```text
                    Incoming Telemetry
                           │
                           ▼
                 Telemetry Validation
                           │
                           ▼
                 Recent Asset History
                           │
                           ▼
                  Feature Engineering
                           │
                           ▼
                 58 Model Features
                           │
                           ▼
                 ML Scoring Function
                           │
                           ▼
              ┌────────────────────────┐
              │     XGBoost Model      │
              └────────────────────────┘
                           │
                           ▼
                  Prediction Result
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
          Alert Logic              Maintenance Logic
             │                           │
             └─────────────┬─────────────┘
                           ▼
                       API / DB
                           │
                           ▼
                       Frontend
```

---

# 11. Rolling-Feature Requirement

Because the model uses rolling windows of:

```text
5 minutes
15 minutes
60 minutes
```

the backend needs access to recent telemetry history for each asset.

A single isolated telemetry record is therefore not enough to reconstruct all model features.

For example:

```text
vibration_mm_s_rolling_mean_5
```

requires recent vibration observations.

Similarly:

```text
temperature_c_rolling_mean_60
```

requires the relevant recent temperature history.

The backend implementation should therefore maintain or query recent telemetry for each asset.

---

# 12. Recommended Backend Feature Service

The backend should preferably separate feature preparation from prediction.

Recommended conceptual components:

```text
TelemetryService
       │
       ▼
FeatureEngineeringService
       │
       ▼
PredictionService
       │
       ▼
AlertService
```

### TelemetryService

Responsible for:

* Receiving telemetry.
* Validating telemetry.
* Persisting telemetry.
* Retrieving recent telemetry history.

### FeatureEngineeringService

Responsible for:

* Constructing the 58 model features.
* Maintaining the same feature names and calculations used during training.
* Handling rolling windows and lag calculations.
* Preparing categorical fields.

### PredictionService

Responsible for:

* Calling `score_telemetry()`.
* Returning the model prediction.
* Recording model metadata where appropriate.

### AlertService

Responsible for:

* Deciding whether a prediction should create an application alert.
* Managing alert status.
* Avoiding duplicate alerts.
* Connecting prediction results to maintenance workflows.

The ML scorer itself should remain focused on model inference.

---

# 13. Prediction Response

The current scorer returns:

```json
{
  "failure_probability": 0.73,
  "failure_predicted": true,
  "risk_level": "HIGH",
  "threshold": 0.12,
  "prediction_horizon_hours": 6,
  "target": "failure_next_6h"
}
```

## Field definitions

### `failure_probability`

Numeric probability produced by the XGBoost model.

Example:

```text
0.73
```

means the model assigned a probability of approximately 73%.

This should be treated as a model score, not a guarantee of failure.

### `failure_predicted`

Boolean decision based on the saved threshold.

```text
true
```

when:

```text
failure_probability >= 0.12
```

Otherwise:

```text
false
```

### `risk_level`

Application-facing classification:

```text
HIGH
MEDIUM
LOW
```

### `threshold`

The model's decision threshold:

```text
0.12
```

### `prediction_horizon_hours`

Always:

```text
6
```

for this model.

### `target`

Always:

```text
failure_next_6h
```

for this model.

---

# 14. Risk Classification

The current scorer applies:

```text
Probability >= 0.50
        ↓
       HIGH

0.12 <= Probability < 0.50
        ↓
      MEDIUM

Probability < 0.12
        ↓
       LOW
```

Therefore:

| Probability | Risk   | Failure predicted |
| ----------: | ------ | ----------------- |
| 0.00–0.1199 | LOW    | No                |
| 0.12–0.4999 | MEDIUM | Yes               |
|   0.50–1.00 | HIGH   | Yes               |

The backend should not create a separate threshold unless product requirements explicitly change.

---

# 15. Example Backend Integration

A simplified Python integration is:

```python
from ml.scoring import score_telemetry


def predict_asset_failure(feature_payload):
    result = score_telemetry(feature_payload)

    return {
        "failure_probability": result["failure_probability"],
        "failure_predicted": result["failure_predicted"],
        "risk_level": result["risk_level"],
        "threshold": result["threshold"],
        "prediction_horizon_hours": result["prediction_horizon_hours"],
        "target": result["target"],
    }
```

The backend should pass the feature-engineered payload:

```python
feature_payload = {
    # Exact 58 model features
    # retrieved/generated by the feature engineering layer
}
```

Do not hard-code only the six raw sensor values.

---

# 16. Example API Response

The backend may expose the ML result through an equipment-health endpoint.

Example:

```json
{
  "asset_id": "PUMP-001",
  "prediction": {
    "failure_probability": 0.73,
    "failure_predicted": true,
    "risk_level": "HIGH",
    "threshold": 0.12,
    "prediction_horizon_hours": 6,
    "target": "failure_next_6h"
  }
}
```

The backend may add application information around this result, for example:

```json
{
  "asset_id": "PUMP-001",
  "asset_type": "PUMP",
  "prediction": {
    "failure_probability": 0.73,
    "failure_predicted": true,
    "risk_level": "HIGH",
    "prediction_horizon_hours": 6
  },
  "recommended_action": "Inspect equipment and assess maintenance requirement"
}
```

The recommended action is **business/application logic**, not an output generated directly by the XGBoost model.

---

# 17. Alert Integration

A prediction should not automatically be treated as a confirmed equipment failure.

Recommended workflow:

```text
Prediction
    │
    ├── LOW
    │     └── Monitor
    │
    ├── MEDIUM
    │     └── Generate warning / monitoring alert
    │
    └── HIGH
          └── Generate high-priority maintenance alert
```

The exact alert policy belongs to the application/business layer.

For example, the backend may choose to:

* Create an alert.
* Notify a maintenance supervisor.
* Recommend inspection.
* Create or suggest a work order.
* Display equipment health on the dashboard.

These actions should remain separate from the ML scorer.

---

# 18. Alert Deduplication

The backend should avoid creating a new alert every time telemetry arrives while an asset remains above the alert threshold.

For example, if:

```text
PUMP-001
```

remains HIGH for 20 consecutive minutes, the system should not necessarily create 20 separate alerts.

A recommended approach is:

```text
Asset + Alert Type + Active State
```

with an existing alert being updated rather than duplicated.

The backend team should define the final alert lifecycle.

Possible states:

```text
OPEN
ACKNOWLEDGED
IN_PROGRESS
RESOLVED
CLOSED
```

---

# 19. Prediction Persistence

Prediction results may be stored for auditability and historical analysis.

A possible prediction record contains:

```text
id
asset_id
prediction_timestamp
failure_probability
failure_predicted
risk_level
threshold
prediction_horizon_hours
model_version
created_at
```

The backend may also retain a reference to the telemetry/feature timestamp used for the prediction.

The model version should be recorded so that historical predictions can be traced to the model that produced them.

---

# 20. Model Versioning

The currently deployed model is represented by:

```text
ml/models/maintainnexus_xgboost.json
```

The metadata file:

```text
ml/models/model_metadata.json
```

contains the configuration required by the scorer.

When a future model is retrained, the backend integration should not silently change behavior.

The following should be versioned together:

```text
Model artifact
Model metadata
Feature definitions
Threshold
Model evaluation results
```

A future model may have:

* A different feature set.
* A different threshold.
* A different prediction horizon.
* Different performance.

Those changes must be treated as a model version update.

---

# 21. Categorical Features

The model uses four categorical features:

```text
asset_id
asset_type
operating_state
alarm_code
```

The scorer restores their categorical values using the categories stored in:

```text
model_metadata.json
```

The backend should therefore send valid values using the same semantic definitions used during training.

The backend should not arbitrarily transform these values into unrelated codes.

For example, if:

```text
asset_type = PUMP
```

was used during training, the backend should preserve the corresponding semantic value.

---

# 22. Unknown Categorical Values

The backend should validate categorical values before calling the scorer.

Potential examples include:

```text
Unknown asset ID
Unknown asset type
Unknown operating state
Unknown alarm code
```

The backend should not silently invent a category.

Recommended handling:

```text
Validate
   ↓
Known value?
 ┌─┴─┐
Yes  No
 │    │
 ▼    ▼
Score  Handle validation error
```

The exact fallback behavior should be agreed with the backend team.

---

# 23. Missing Model Features

The scorer already validates missing model features.

If required features are absent, it raises:

```text
ValueError
```

with the missing feature names.

The backend should convert this into an appropriate API/application error rather than returning a misleading prediction.

For example:

```json
{
  "error": "Unable to generate prediction",
  "reason": "Required model features are unavailable"
}
```

The backend should log the actual missing fields internally.

---

# 24. Insufficient Telemetry History

Rolling features require historical observations.

If the backend does not have enough telemetry to calculate the required windows, it should not fabricate values merely to obtain a prediction.

Recommended behavior:

```text
Insufficient history
        ↓
No prediction
        ↓
Return "prediction unavailable"
        ↓
Continue collecting telemetry
```

This is preferable to silently producing a potentially unreliable prediction.

---

# 25. Data Quality Requirements

Telemetry used for prediction should satisfy basic quality requirements:

* Valid timestamp.
* Valid asset ID.
* Valid sensor values.
* No unexpected duplicate records.
* Correct units.
* Correct sampling interpretation.
* Valid categorical operational fields.

The ML data pipeline already includes a data-quality gate.

The backend should apply appropriate runtime validation before prediction.

---

# 26. Units

The current model expects the following sensor fields and units:

| Feature              | Unit |
| -------------------- | ---- |
| `pressure_bar`       | bar  |
| `temperature_c`      | °C   |
| `flow_rate_m3h`      | m³/h |
| `motor_current_a`    | A    |
| `vibration_mm_s`     | mm/s |
| `valve_position_pct` | %    |

The backend must preserve these units.

Do not send:

```text
temperature_f
```

where:

```text
temperature_c
```

is expected.

Likewise, do not change pressure or flow units without converting them first.

---

# 27. Prediction Frequency

The original telemetry is sampled at:

```text
1-minute intervals
```

The backend team should determine the production prediction frequency based on the application's operational requirements.

The model can conceptually be evaluated whenever sufficient updated telemetry is available.

However, prediction frequency and alert frequency are different concerns.

For example:

```text
Telemetry: every 1 minute
Prediction: every 1 minute
Alert: only when risk state changes / alert policy triggers
```

This avoids creating excessive duplicate alerts.

---

# 28. Do Not Retrain in the Backend

The backend must only perform inference.

Do not place:

```text
model.fit()
```

or model-training logic inside the API.

The separation is:

```text
ML development/training
        ↓
Saved model artifact
        ↓
Backend inference
```

Model retraining remains an ML/data pipeline responsibility.

---

# 29. Do Not Recalculate the Threshold

The current production threshold is:

```text
0.12
```

It was selected using the validation dataset based on F1 score.

The test set was evaluated using that validation-selected threshold.

The backend should therefore use the threshold supplied by:

```text
model_metadata.json
```

rather than independently selecting a new threshold.

---

# 30. Important Distinction: Probability vs Risk

The following are different concepts:

```text
failure_probability
```

is the model output.

```text
failure_predicted
```

is the binary decision based on the threshold.

```text
risk_level
```

is the application-friendly classification.

Example:

```text
failure_probability = 0.30

failure_predicted = true

risk_level = MEDIUM
```

This does **not** mean the equipment will definitely fail.

It means the model has assigned a probability above its operational decision threshold.

---

# 31. Feature Importance

The finalized model's strongest features include:

| Feature                           | Importance |
| --------------------------------- | ---------: |
| `vibration_mm_s_rolling_mean_5`   |   0.264813 |
| `motor_current_a_rolling_mean_60` |   0.096662 |
| `vibration_mm_s_rolling_mean_15`  |   0.081528 |
| `temperature_c_rolling_mean_60`   |   0.074903 |
| `asset_type`                      |   0.051627 |
| `temperature_c`                   |   0.048920 |
| `vibration_mm_s_rolling_mean_60`  |   0.045038 |
| `vibration_mm_s`                  |   0.037505 |
| `pressure_bar_rolling_mean_60`    |   0.030220 |
| `temperature_c_rolling_mean_5`    |   0.029254 |

This indicates that recent vibration behavior, motor current, and temperature trends are important predictors in the current model.

Feature importance should be treated as an ML diagnostic, not as a direct maintenance diagnosis.

---

# 32. Health Dashboard Integration

The frontend may display:

```text
Asset
Current Health Risk
Failure Probability
Prediction Horizon
Last Prediction
```

Example:

```text
PUMP-001

Risk: HIGH
Failure probability: 73%
Prediction horizon: 6 hours
Last updated: 10:32
```

The frontend should consume the backend API rather than loading the XGBoost model directly.

Architecture:

```text
Frontend
   ↓
Backend API
   ↓
Prediction Service
   ↓
ML Scorer
   ↓
XGBoost
```

The Flutter frontend should not contain Python/XGBoost inference logic.

---

# 33. Maintenance Workflow Integration

The ML prediction can support the existing maintenance workflow.

Example:

```text
HIGH prediction
       ↓
Create maintenance alert
       ↓
Maintenance supervisor reviews
       ↓
Inspection
       ↓
Work order if required
       ↓
Maintenance performed
       ↓
Alert resolved
```

The model should **support maintenance decisions**, not automatically declare an equipment failure.

---

# 34. Error Handling

The backend should handle at least:

### Missing features

```text
400 / 422
```

depending on the API convention.

### Invalid telemetry

```text
400 / 422
```

### Insufficient history

A suitable application response such as:

```text
Prediction unavailable
```

rather than a false prediction.

### Model loading failure

This is a server-side configuration/deployment problem and should produce an appropriate:

```text
500
```

response while logging the underlying exception.

### Unexpected inference error

Log the exception and return a controlled API error.

Do not expose internal stack traces to end users.

---

# 35. Deployment Requirements

The backend deployment environment must include the ML runtime dependencies required by the scorer.

The scorer currently depends on:

```text
Python
pandas
xgboost
```

The deployed backend environment must have compatible versions.

The saved model was trained with:

```text
XGBoost 3.4.1
```

The deployment should use the same or a compatible XGBoost version unless the model has been explicitly validated against another version.

The model artifact must be available at:

```text
ml/models/maintainnexus_xgboost.json
```

and metadata at:

```text
ml/models/model_metadata.json
```

---

# 36. Docker Considerations

If the backend is containerized, ensure that the ML package and model artifacts are included in the backend image.

The container must be able to resolve:

```text
ml.scoring
```

and access:

```text
ml/models/maintainnexus_xgboost.json
ml/models/model_metadata.json
```

Do not rely on the developer's local Windows path.

The deployment path must be resolved relative to the application package/project structure.

---

# 37. Testing Requirements

Before considering backend integration complete, the backend team should test:

### Test 1 — Normal telemetry

Expected:

```text
Prediction returned successfully
```

### Test 2 — High-risk telemetry

Expected:

```text
Prediction returned successfully
risk_level = HIGH
```

where the supplied feature set genuinely produces a high model probability.

### Test 3 — Missing feature

Expected:

```text
Controlled validation error
```

### Test 4 — Invalid categorical value

Expected:

```text
Controlled validation behavior
```

### Test 5 — Insufficient history

Expected:

```text
Prediction unavailable
```

rather than fabricated rolling features.

### Test 6 — Model unavailable

Expected:

```text
Controlled server-side error
```

### Test 7 — Repeated high-risk predictions

Expected:

```text
No uncontrolled duplicate alert creation
```

---

# 38. Integration Acceptance Criteria

The backend integration can be considered complete when:

* [ ] Backend receives valid telemetry.
* [ ] Telemetry is persisted or otherwise available for feature generation.
* [ ] Required recent telemetry history can be retrieved per asset.
* [ ] The 58 model features can be generated consistently.
* [ ] Feature names match `model_metadata.json`.
* [ ] Leakage fields are excluded.
* [ ] Calendar fields excluded from the final model are not supplied as model features.
* [ ] Categorical values are handled correctly.
* [ ] `score_telemetry()` is called for inference.
* [ ] Failure probability is returned.
* [ ] Threshold `0.12` is respected.
* [ ] Risk classification is returned.
* [ ] Prediction horizon is reported as 6 hours.
* [ ] Prediction results can be persisted if required.
* [ ] Alerts are generated according to application rules.
* [ ] Duplicate alerts are controlled.
* [ ] Frontend can retrieve prediction results through the backend API.
* [ ] Automated tests cover successful and failure scenarios.
* [ ] Docker deployment can load the model.
* [ ] Model version is traceable.

---

# 39. What the Backend Developer Should NOT Change

Unless a new ML version is formally approved, do not change:

```text
Target:
failure_next_6h

Prediction horizon:
6 hours

Threshold:
0.12

Model:
XGBoost

Model artifact:
ml/models/maintainnexus_xgboost.json
```

Do not:

* Retrain the model from the backend.
* Change the prediction threshold.
* Remove required engineered features.
* Add leakage fields.
* Replace engineered features with raw sensor values.
* Create a second independent prediction formula.
* Put ML inference in the Flutter application.
* Treat predictions as confirmed failures.
* Generate unlimited duplicate alerts.

---

# 40. Current ML Handoff

The ML implementation is complete and committed to the repository.

Current commit:

```text
a426d0e
Complete predictive maintenance XGBoost model pipeline
```

Branch:

```text
ml/feature-with-automation-upgrade
```

The backend developer should integrate against the committed ML implementation rather than modifying the model as part of normal backend development.

---

# 41. Recommended Integration Sequence

The backend team should implement the integration in this order:

```text
Step 1
Verify ML package/model can be imported
        ↓
Step 2
Verify telemetry storage/retrieval
        ↓
Step 3
Implement feature preparation
        ↓
Step 4
Generate the 58 required features
        ↓
Step 5
Call score_telemetry()
        ↓
Step 6
Expose prediction through backend API
        ↓
Step 7
Persist prediction results
        ↓
Step 8
Integrate prediction with alert workflow
        ↓
Step 9
Integrate dashboard/frontend
        ↓
Step 10
Run end-to-end tests
```

This sequence keeps ML inference separate from application logic and makes failures easier to diagnose.

---

# 42. Final Contract

The essential contract between the ML and backend teams is:

```text
INPUT
-----
58 model-compatible engineered features


PROCESS
-------
score_telemetry(feature_payload)


MODEL
-----
XGBoost 3.4.1


TARGET
------
failure_next_6h


HORIZON
-------
6 hours


THRESHOLD
---------
0.12


OUTPUT
------
failure_probability
failure_predicted
risk_level
threshold
prediction_horizon_hours
target
```

The backend owns **data delivery, API exposure, persistence, alerts, maintenance workflows, and frontend integration**.

The ML component owns **feature definitions, model inference, model metadata, threshold selection, evaluation, and future model versions**.

This separation should be maintained as the system evolves.
