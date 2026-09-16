# MaintainNexusAI — Predict → Decide → Act → Learn

**Document:** End-to-End Operational Intelligence Contract
**System:** MaintainNexusAI
**Version:** 1.0
**Status:** Implementation Handoff
**Primary Use Case:** Predict failure/disruption of pumps, loading arms, and valves and enable timely operational mitigation.

---

## 1. Purpose

MaintainNexusAI is designed to move beyond simply predicting equipment failure.

The complete operational flow is:

```text
Telemetry
   ↓
Feature Engineering
   ↓
PREDICT
   ↓
DECIDE
   ↓
ACT
   ↓
LEARN
   ↺
```

The ML component currently provides the **Predict** capability.

The backend/application layer must integrate the prediction capability with business decision rules, operational actions, and outcome capture to complete the full predictive-maintenance loop.

This document defines that end-to-end contract.

---

# 2. Current Implementation Status

| Stage                                | Status                          | Owner           |
| ------------------------------------ | ------------------------------- | --------------- |
| Telemetry ingestion                  | Implemented in ML/data pipeline | ML/Data         |
| Data quality validation              | Implemented                     | ML/Data         |
| Unified operational data             | Implemented                     | ML/Data         |
| Failure target generation            | Implemented                     | ML              |
| Feature engineering                  | Implemented                     | ML              |
| Temporal train/validation/test split | Implemented                     | ML              |
| XGBoost model training               | Implemented                     | ML              |
| Model evaluation                     | Implemented                     | ML              |
| Real-time scorer                     | Implemented                     | ML              |
| Prediction API integration           | To be implemented               | Backend         |
| Business decision engine             | Implemented                     | Backend         |
| Alert generation                     | To be implemented               | Backend         |
| Operational mitigation workflow      | Implemented for loading-point rerouting | Backend/Product |
| Outcome/feedback capture             | Implemented for operational actions | Backend         |
| Model monitoring/retraining workflow | Future phase                    | ML/Data         |

Therefore, the current implementation supports the loading-point golden path:
the internal decision engine can mark a bay unavailable, reassign a scheduled
truck to an alternate bay, and persist the decision, action, and outcome. The
browser exposes read-only decision and loading-point views at `/operations` to
engineers, supervisors, and executives. Broader decision policies and model
monitoring remain future work.

---

# 3. MaintainNexusAI Use Case

The primary use case is monitoring critical equipment involved in petroleum-terminal operations:

* Pumps
* Loading arms
* Valves

A failure or disruption involving one of these assets may affect:

* Equipment availability
* Loading operations
* Truck turnaround
* Product movement
* Maintenance response
* Operational continuity
* Downtime

The objective is therefore not simply:

> "Predict that an asset will fail."

The objective is:

> **Predict an impending failure, determine its operational significance, trigger the appropriate response, and capture the outcome so that future decisions can improve.**

---

# 4. PREDICT

## 4.1 Prediction Objective

The current ML model predicts:

> **Whether an equipment failure event will occur within the next 6 hours.**

Target:

```text
failure_next_6h
```

Target values:

```text
0 = No failure within the next 6 hours
1 = Failure within the next 6 hours
```

---

## 4.2 Model

Current production candidate:

```text
Model: XGBoost
Version: 3.4.1
Task: Binary classification
Prediction horizon: 6 hours
Model features: 58
Decision threshold: 0.12
```

Model artifacts:

```text
ml/models/maintainnexus_xgboost.json
ml/models/model_metadata.json
ml/models/feature_importance.csv
```

The model must not be retrained or have its threshold changed by the backend application.

---

# 5. Prediction Inputs

The model ultimately requires **58 engineered features**.

The backend must not send only the six raw sensor measurements to the scorer.

The core raw telemetry variables are:

```text
pressure_bar
temperature_c
flow_rate_m3h
motor_current_a
vibration_mm_s
valve_position_pct
```

The feature-engineering layer derives historical features including:

* 1-minute lag
* 1-minute delta
* 5-minute rolling mean
* 5-minute rolling standard deviation
* 15-minute rolling mean
* 15-minute rolling standard deviation
* 60-minute rolling mean
* 60-minute rolling standard deviation

Categorical inputs include:

```text
asset_id
asset_type
operating_state
alarm_code
```

The final model deliberately excludes calendar features:

```text
hour
day_of_week
month
is_weekend
```

This prevents the model from relying on synthetic calendar artifacts rather than equipment behaviour.

---

# 6. Prediction Output

The ML scorer returns:

```json
{
  "failure_probability": 0.82,
  "failure_predicted": true,
  "risk_level": "HIGH",
  "threshold": 0.12,
  "prediction_horizon_hours": 6,
  "target": "failure_next_6h"
}
```

### Field definitions

| Field                      | Meaning                                               |
| -------------------------- | ----------------------------------------------------- |
| `failure_probability`      | Model-estimated probability of failure within 6 hours |
| `failure_predicted`        | Binary prediction using the 0.12 threshold            |
| `risk_level`               | Application-facing risk classification                |
| `threshold`                | Current ML decision threshold                         |
| `prediction_horizon_hours` | Prediction window                                     |
| `target`                   | Target used by the model                              |

---

# 7. DECIDE

Prediction alone should not automatically result in the same operational response for every asset.

The Decide layer converts the ML prediction into an operational decision.

## 7.1 Risk Rules

The current risk classification is:

```text
Probability < 0.12
        ↓
LOW

0.12 ≤ Probability < 0.50
        ↓
MEDIUM

Probability ≥ 0.50
        ↓
HIGH
```

The model prediction threshold remains:

```text
failure_probability >= 0.12
        ↓
failure_predicted = TRUE
```

---

# 8. Decision Matrix

The backend should implement an initial decision policy similar to:

| Risk   | Prediction | Initial Decision                              |
| ------ | ---------- | --------------------------------------------- |
| LOW    | False      | Continue monitoring                           |
| LOW    | True       | Not applicable under current threshold        |
| MEDIUM | True       | Generate preventive alert/review              |
| HIGH   | True       | Escalate for immediate operational assessment |
| HIGH   | False      | Not applicable under current risk rules       |

The final operational action may additionally depend on:

* Asset type
* Asset criticality
* Current operating state
* Existing maintenance activity
* Existing open alerts
* Loading operation affected
* Availability of alternative equipment
* Maintenance team availability

---

# 9. Asset Criticality

Risk level and asset criticality must not be treated as the same thing.

For example:

```text
PUMP-001
Probability = 0.18
Risk = MEDIUM
Criticality = CRITICAL
```

may require more urgent treatment than:

```text
VALVE-014
Probability = 0.35
Risk = MEDIUM
Criticality = LOW
```

Therefore, the backend should maintain an asset-criticality attribute independently from the ML probability.

Recommended criticality values:

```text
CRITICAL
HIGH
MEDIUM
LOW
```

This allows the decision engine to combine:

```text
ML Risk
+
Asset Criticality
+
Operational Context
=
Operational Decision
```

---

# 10. Decision Examples

## Example A — LOW

```text
Asset: VALVE-008
Probability: 0.05
Risk: LOW
```

Decision:

```text
Continue normal monitoring.
Do not create a maintenance escalation.
```

The prediction can still be stored for monitoring purposes.

---

## Example B — MEDIUM

```text
Asset: PUMP-004
Probability: 0.31
Risk: MEDIUM
```

Decision:

```text
Create preventive maintenance alert.
Notify responsible maintenance personnel.
Continue monitoring the asset.
```

The system should avoid repeatedly creating identical alerts every minute.

---

## Example C — HIGH

```text
Asset: ARM-003
Probability: 0.82
Risk: HIGH
```

Decision:

```text
Escalate immediately.
Create high-priority maintenance alert.
Notify responsible personnel.
Check whether an active loading operation is affected.
Evaluate mitigation/alternative equipment.
```

---

# 11. ACT

The Act layer converts the operational decision into an actual system action.

The exact action depends on the decision.

## 11.1 Alert Creation

For qualifying predictions, the backend may create a maintenance alert containing:

```text
alert_id
asset_id
asset_type
prediction_timestamp
failure_probability
risk_level
prediction_horizon_hours
decision
status
priority
```

Example:

```json
{
  "asset_id": "PUMP-004",
  "risk_level": "HIGH",
  "failure_probability": 0.82,
  "prediction_horizon_hours": 6,
  "decision": "IMMEDIATE_INTERVENTION",
  "priority": "CRITICAL"
}
```

---

# 12. Alert Deduplication

Because telemetry may arrive every minute, the same asset could produce repeated HIGH predictions.

The system must not create:

```text
Alert 1 → 10:00
Alert 2 → 10:01
Alert 3 → 10:02
Alert 4 → 10:03
...
```

for the same unresolved condition.

Instead, the backend should maintain an active prediction/alert state.

Conceptually:

```text
New prediction
      ↓
Does an active alert exist for this asset?
      ↓
   YES ─────────→ Update existing alert
      │
      NO
      ↓
Create new alert
```

A new alert should normally be generated when:

* The previous alert has been resolved, or
* A new failure episode is detected, or
* The operational rules explicitly permit escalation.

---

# 13. Operational Mitigation

MaintainNexusAI's purpose extends beyond maintenance notification.

Where operational data is available, the system should determine whether a predicted equipment failure could affect an active operation.

For example:

```text
PUMP-004
    ↓
HIGH failure risk
    ↓
Check active operations
    ↓
PUMP-004 is supporting loading operation LO-102
    ↓
Flag LO-102 as potentially affected
    ↓
Notify responsible operations team
    ↓
Evaluate available alternative equipment
```

Potential mitigation actions include:

* Flag affected loading operation
* Notify operations personnel
* Recommend alternative equipment
* Recommend inspection before continued operation
* Escalate to maintenance
* Place operation into a review state
* Create a maintenance work request

### Important

Automatic physical control of pumps, valves, or loading equipment is **not part of the current ML implementation**.

Any automated control action must first be explicitly approved through the system's operational and safety requirements.

---

# 14. Human-in-the-Loop

The initial MaintainNexusAI implementation should maintain human oversight.

The system should recommend and trigger workflow actions rather than silently making safety-critical decisions.

Recommended flow:

```text
ML Prediction
      ↓
Decision Engine
      ↓
Recommendation / Alert
      ↓
Human Review
      ↓
Operational Action
      ↓
Outcome Recorded
```

This is particularly important for high-criticality petroleum-terminal equipment.

---

# 15. LEARN

The Learn layer closes the feedback loop.

Every meaningful prediction should eventually be compared with what actually happened.

The system must capture the outcome of the prediction.

---

# 16. Prediction Record

The backend should persist a prediction record containing at least:

```text
prediction_id
asset_id
asset_type
prediction_timestamp
failure_probability
risk_level
failure_predicted
threshold
prediction_horizon_hours
model_version
```

Recommended additional fields:

```text
decision
alert_id
action_taken
action_timestamp
outcome
actual_failure
actual_failure_timestamp
maintenance_completed
maintenance_completion_timestamp
downtime_minutes
```

---

# 17. Action Feedback

When an alert results in an action, the system should capture:

```text
Action:
INSPECTION
MAINTENANCE
OPERATIONAL_MITIGATION
NO_ACTION
ESCALATION
OTHER
```

The user should also be able to record why an alert was not acted upon.

Example:

```text
Prediction:
HIGH

Action:
INSPECTION

Result:
Bearing degradation detected

Maintenance:
Bearing replaced

Outcome:
Failure avoided
```

---

# 18. Actual Outcome

After the prediction window expires, the system should determine the actual outcome.

Example:

```text
Prediction at 10:00
        ↓
Predicted failure within 6h
        ↓
6-hour window ends at 16:00
        ↓
Did failure occur?
```

Possible outcomes:

```text
TRUE_POSITIVE
FALSE_POSITIVE
TRUE_NEGATIVE
FALSE_NEGATIVE
```

For operational learning, additional outcomes may include:

```text
FAILURE_OCCURRED
FAILURE_PREVENTED
MAINTENANCE_REQUIRED
NO_ISSUE_FOUND
OPERATION_INTERRUPTED
OPERATION_CONTINUED
```

---

# 19. Learning Dataset

The accumulated prediction and outcome records should eventually form a feedback dataset.

Conceptually:

```text
prediction
+
decision
+
action
+
actual outcome
=
learning record
```

Example:

| Field                  | Example       |
| ---------------------- | ------------- |
| asset_id               | PUMP-004      |
| prediction_probability | 0.82          |
| risk_level             | HIGH          |
| action_taken           | INSPECTION    |
| actual_failure         | TRUE          |
| maintenance_completed  | TRUE          |
| downtime_minutes       | 35            |
| outcome                | TRUE_POSITIVE |

This dataset can later be used for:

* Model performance monitoring
* Threshold evaluation
* False-positive analysis
* False-negative analysis
* Drift detection
* Feature analysis
* Model retraining

---

# 20. Model Learning Is Not Immediate Online Retraining

The first implementation should **not automatically retrain the XGBoost model every time an outcome is recorded**.

Instead:

```text
Operational feedback
        ↓
Feedback dataset
        ↓
Model monitoring
        ↓
Scheduled ML review
        ↓
Retraining experiment
        ↓
Validation
        ↓
Approval
        ↓
New model version
```

This protects the production model from uncontrolled changes.

---

# 21. Model Versioning

Every prediction must identify the model version that generated it.

Example:

```text
model_version = maintainnexus-xgboost-1.0
```

If a future model is deployed:

```text
maintainnexus-xgboost-1.1
```

historical predictions must continue to reference the original version.

This allows the team to answer:

> Which model generated this alert?

---

# 22. End-to-End Architecture

The recommended application flow is:

```text
                   TELEMETRY
                       │
                       ▼
             ┌──────────────────┐
             │ Telemetry Service│
             └────────┬─────────┘
                      │
                      ▼
             ┌──────────────────┐
             │ Feature Engine   │
             │                  │
             │ Lag / Delta /    │
             │ Rolling features │
             └────────┬─────────┘
                      │
                      ▼
             ┌──────────────────┐
             │ Prediction       │
             │ Service          │
             │                  │
             │ XGBoost          │
             └────────┬─────────┘
                      │
                      ▼
             ┌──────────────────┐
             │ Decision Engine  │
             │                  │
             │ Risk + Critical- │
             │ ity + Context    │
             └────────┬─────────┘
                      │
             ┌────────┴─────────┐
             ▼                  ▼
       ┌───────────┐      ┌──────────────┐
       │ Alert     │      │ Operations / │
       │ Service   │      │ Maintenance  │
       └─────┬─────┘      └──────┬───────┘
             │                   │
             └─────────┬─────────┘
                       ▼
                ┌──────────────┐
                │ Outcome /    │
                │ Feedback     │
                └──────┬───────┘
                       │
                       ▼
                ┌──────────────┐
                │ ML Monitoring│
                │ & Learning   │
                └──────────────┘
```

---

# 23. Responsibility Boundaries

## ML/Data Team

Responsible for:

* Data pipelines
* Feature engineering
* Model training
* Model evaluation
* Model artifacts
* Model metadata
* Scoring logic
* Model versioning
* Performance monitoring
* Future retraining

## Backend Team

Responsible for:

* Prediction service integration
* Receiving telemetry
* Supplying required engineered features
* Calling the scorer/model service
* Persisting predictions
* Implementing decision rules
* Alert creation
* Alert deduplication
* Operational workflow
* Action tracking
* Outcome capture
* APIs consumed by frontend

## Frontend Team

Responsible for presenting:

* Asset risk
* Failure probability
* Risk level
* Prediction horizon
* Active alerts
* Recommended action
* Action status
* Maintenance status
* Historical outcomes

The frontend must not execute the Python/XGBoost model.

---

# 24. Important Feature Engineering Requirement

The model requires historical telemetry.

For an asset:

```text
Current reading
+
Recent telemetry history
        ↓
Feature calculation
        ↓
58 model features
        ↓
Prediction
```

The backend must therefore retain sufficient recent telemetry history to calculate the rolling features.

At minimum, the feature-engineering implementation must support the longest required rolling window:

```text
60 minutes
```

The exact production buffering/storage mechanism is a backend architecture decision.

---

# 25. Prediction Frequency

The initial implementation may evaluate an asset whenever a new valid telemetry observation is available.

For 1-minute telemetry:

```text
New telemetry
     ↓
Update rolling history
     ↓
Calculate features
     ↓
Generate prediction
```

However, alert creation must remain subject to deduplication and decision rules.

The system should distinguish between:

```text
Prediction frequency
```

and:

```text
Alert frequency
```

They are not necessarily the same.

---

# 26. Edge Cases

The backend must handle the following conditions.

## 26.1 Insufficient History

If an asset does not have sufficient telemetry history to calculate the required rolling features:

```text
Do not generate an invalid prediction.
```

Return an appropriate state such as:

```text
INSUFFICIENT_DATA
```

---

## 26.2 Missing Telemetry

If required telemetry fields are missing:

```text
Do not silently substitute arbitrary values.
```

The system should:

1. Validate the telemetry.
2. Determine whether safe feature calculation is possible.
3. If not, mark the prediction unavailable.
4. Log the reason.

---

## 26.3 Unknown Categorical Value

The model expects known categories for:

```text
asset_id
asset_type
operating_state
alarm_code
```

An unknown category must not silently be converted into a misleading value.

The backend should reject or quarantine the prediction request and log the issue for investigation.

---

## 26.4 Duplicate Telemetry

Duplicate telemetry should not cause duplicate predictions or duplicate alerts.

---

## 26.5 Out-of-Order Telemetry

Telemetry arriving out of chronological order must be handled before rolling features are calculated.

---

## 26.6 Existing Maintenance

If an asset is already under maintenance:

```text
HIGH prediction
      ↓
Check maintenance status
      ↓
Existing maintenance?
      ↓
Update/associate existing workflow
```

Do not automatically create redundant work orders.

---

## 26.7 Existing Alert

If an active alert exists for the asset:

```text
Update existing alert
```

rather than continuously creating new alerts.

---

## 26.8 Asset Offline

If telemetry stops arriving, the system should distinguish:

```text
No failure prediction
```

from:

```text
No telemetry available
```

An unavailable prediction is not equivalent to a LOW-risk prediction.

---

# 27. Safety Principle

The following states must remain distinct:

```text
LOW RISK
```

```text
NO PREDICTION
```

```text
INSUFFICIENT DATA
```

```text
SYSTEM ERROR
```

They must never all be represented as:

```text
LOW
```

A missing prediction does not mean that the equipment is healthy.

---

# 28. Monitoring Metrics

The backend/application should monitor operational metrics such as:

### Prediction metrics

* Number of predictions
* Number of HIGH predictions
* Number of MEDIUM predictions
* Number of LOW predictions
* Prediction latency
* Prediction failures

### Alert metrics

* Alerts generated
* Alerts acknowledged
* Alerts resolved
* Alert response time
* Duplicate alerts prevented

### Operational metrics

* Actions taken
* Maintenance interventions
* Downtime
* Affected operations
* Prevented/avoided failures where measurable

### ML metrics

* Precision
* Recall
* F1
* False-positive rate
* False-negative rate
* PR-AUC
* Prediction distribution
* Model drift

---

# 29. Current Model Baseline

The finalized test-set baseline is:

```text
Precision: 94.16%
Recall:    52.05%
F1:        67.04%
ROC-AUC:   76.55%
PR-AUC:    55.35%
```

Confusion matrix:

```text
                 Predicted
                 0       1

Actual 0       305351   166
Actual 1         2464  2675
```

These metrics are the current baseline for future model comparisons.

A future model should not replace this model simply because one metric improves.

The team should compare the complete operational impact.

---

# 30. Decision Quality vs Model Quality

The backend team must understand that:

```text
Model probability
≠
Operational decision
```

For example:

```text
Probability = 0.18
```

does not by itself mean:

```text
Create emergency maintenance work order.
```

The decision should consider:

```text
Probability
+
Risk level
+
Asset criticality
+
Operational context
+
Existing alerts
+
Maintenance status
```

---

# 31. API-Level Concept

The backend should expose a prediction result to the application layer.

Conceptually:

```http
POST /api/predictions
```

Request:

```json
{
  "asset_id": "PUMP-004",
  "telemetry_timestamp": "2026-01-20T10:30:00",
  "features": {
    "...": "58 required model features"
  }
}
```

Response:

```json
{
  "prediction_id": "pred-001",
  "asset_id": "PUMP-004",
  "failure_probability": 0.82,
  "failure_predicted": true,
  "risk_level": "HIGH",
  "threshold": 0.12,
  "prediction_horizon_hours": 6,
  "model_version": "maintainnexus-xgboost-1.0",
  "decision": "IMMEDIATE_INTERVENTION"
}
```

The exact endpoint naming is a backend implementation decision.

---

# 32. End-to-End Example

Consider:

```text
Asset: ARM-003
Asset type: LOADING_ARM
```

New telemetry arrives.

### Step 1 — Predict

Feature engineering calculates the required historical features.

The model returns:

```text
Probability = 0.82
Prediction = TRUE
Risk = HIGH
Horizon = 6 hours
```

### Step 2 — Decide

Decision engine evaluates:

```text
Risk = HIGH
Asset criticality = CRITICAL
Active loading operation = YES
Existing maintenance = NO
```

Decision:

```text
IMMEDIATE_INTERVENTION
```

### Step 3 — Act

The system:

```text
Create high-priority alert
        ↓
Notify responsible maintenance team
        ↓
Flag affected loading operation
        ↓
Recommend operational assessment
```

A human operator confirms the appropriate action.

### Step 4 — Learn

The system later records:

```text
Inspection performed = YES
Actual failure = TRUE
Maintenance performed = YES
Downtime = 25 minutes
Outcome = TRUE_POSITIVE
```

The record becomes part of the feedback dataset.

---

# 33. Acceptance Criteria

The complete MaintainNexusAI operational loop will be considered implemented when:

### Predict

* [ ] New valid telemetry can produce engineered model features.
* [ ] The finalized XGBoost model can generate a prediction.
* [ ] Prediction uses the saved model threshold of `0.12`.
* [ ] Prediction returns probability, binary prediction, risk, and horizon.
* [ ] Model version is recorded.

### Decide

* [ ] LOW/MEDIUM/HIGH risk is correctly interpreted.
* [ ] Asset criticality can influence operational decisions.
* [ ] Existing alerts and maintenance status are considered.
* [x] Loading-point reroute decisions are persisted/auditable.

### Act

* [ ] Qualifying predictions can create alerts.
* [ ] Alerts are associated with the correct asset.
* [ ] Duplicate alerts are prevented.
* [ ] Responsible personnel can be notified.
* [ ] Affected operations can be identified where operational data exists.
* [x] Loading-point actions taken can be recorded.
* [x] Human approval remains separate for safety-critical physical repair actions.

### Learn

* [ ] Predictions are persisted.
* [ ] Actions are persisted.
* [x] Operational action outcomes are persisted.
* [ ] Predictions can be matched to actual failures.
* [ ] False positives and false negatives can be identified.
* [ ] Maintenance outcomes can be recorded.
* [ ] Model performance can be monitored over time.
* [ ] Historical predictions retain their model version.

---

# 34. Implementation Sequence

The backend team should implement the flow in this order:

```text
1. Telemetry ingestion
        ↓
2. Feature history/storage
        ↓
3. Feature engineering integration
        ↓
4. Prediction service
        ↓
5. Prediction persistence
        ↓
6. Decision engine
        ↓
7. Alert generation
        ↓
8. Alert deduplication
        ↓
9. Operational action workflow
        ↓
10. Action/outcome persistence
        ↓
11. Prediction-vs-outcome evaluation
        ↓
12. ML monitoring
```

Do not begin with automated retraining.

The first priority is to establish a reliable operational feedback loop.

---

# 35. What the ML Team Has Delivered

The ML branch provides:

```text
✓ Data quality pipeline
✓ Unified data layer
✓ Failure target generation
✓ Feature engineering
✓ Temporal splitting
✓ XGBoost training
✓ Model evaluation
✓ Saved model
✓ Model metadata
✓ Feature importance
✓ Real inference scorer
✓ ML/backend integration contract
✓ Product contract
✓ Predict → Decide → Act → Learn contract
```

The backend team should consume these artifacts rather than recreate the ML model independently.

---

# 36. Final System Contract

The intended MaintainNexusAI behaviour is:

```text
                    PREDICT
                       │
                       ▼
             "Could this asset fail
                within 6 hours?"
                       │
                       ▼
                    DECIDE
                       │
                       ▼
            "How serious is this
             prediction in context?"
                       │
                       ▼
                     ACT
                       │
                       ▼
             "What should we do
              about the risk?"
                       │
                       ▼
                    LEARN
                       │
                       ▼
            "What actually happened,
             and was our response
                 effective?"
                       │
                       └──────────────┐
                                      │
                                      ▼
                              Future monitoring
                              and model improvement
```

The system is therefore not complete when the model returns a probability.

The model is one component of a larger operational loop:

> **Predict → Decide → Act → Learn.**

The ML implementation supplies the **Predict** capability. The backend/application implementation completes the operational loop defined in this document.
