import type { Prediction } from "@/lib/api";

export function PredictionDetails({ prediction }: { prediction: Prediction }) {
  return <div className="prediction-details">
    <dl className="prediction-evidence">
      <div><dt>Model decision</dt><dd>{prediction.failure_predicted ? "Failure predicted" : "Failure not predicted"}</dd></div>
      <div><dt>Model risk level</dt><dd>{prediction.risk_level}</dd></div>
      <div><dt>Prediction horizon</dt><dd>{prediction.prediction_horizon_hours} hours</dd></div>
      {prediction.target && <div><dt>Prediction target</dt><dd>{prediction.target}</dd></div>}
      <div><dt>Model version</dt><dd>{prediction.model_version ?? "Not supplied with this evaluation"}</dd></div>
      {prediction.prediction_id && <div><dt>Prediction ID</dt><dd>{prediction.prediction_id}</dd></div>}
      {prediction.timestamp && <div><dt>Prediction time</dt><dd>{new Date(prediction.timestamp).toLocaleString()}</dd></div>}
    </dl>
    {prediction.top_features?.length ? <details><summary>Global model feature importance</summary><p className="monitoring-context">These features have high importance across the trained model. They do not explain this individual prediction.</p><ul>{prediction.top_features.map(feature => <li key={feature}>{feature}</li>)}</ul></details> : null}
    <p className="monitoring-context">This is a model prediction. It does not confirm a physical failure or equipment recovery.</p>
  </div>;
}
