# ML Track

The current `ml/scoring.py` is a placeholder risk function. It is not a trained production model.

## Target
1. Offline historical/external data and provenance.
2. Equipment-specific feature engineering for pumps, loading arms and valves.
3. `failure_within_24h` baseline target.
4. Baseline model + failure-class precision/recall.
5. Versioned model artifact.
6. `POST /api/v1/ml/predict-risk` inference service.
7. Explainable `top_features`.
8. Prediction event.
9. Feedback and monitoring.

See `docs/09-DATA-REQUIREMENTS-MATRIX.md` and `docs/10-ML-BACKEND-CONTRACT.md`.

## GitHub handoff rule
Every ML milestone updates relevant docs/schemas, tests, model version, and the PR description stating which team dependency is unblocked. Never commit real credentials or private KPC data.
