import { TimeSeriesChart, type ChartPoint } from "./time-series-chart";
import type { EquipmentReading } from "@/lib/api";

const metrics = [
  { key: "temperature_c", legacy: "temperature", label: "Temperature", unit: "°C" },
  { key: "vibration_mm_s", legacy: "vibration", label: "Vibration", unit: "mm/s" },
  { key: "pressure_bar", label: "Pressure", unit: "bar" },
  { key: "flow_rate_m3h", label: "Flow rate", unit: "m³/h" },
  { key: "motor_current_a", label: "Motor current", unit: "A" },
  { key: "valve_position_pct", label: "Valve position", unit: "%" },
];

function Trend({ title, unit, points, threshold }: { title: string; unit: string; points: ChartPoint[]; threshold?: number }) {
  return <article className="metric-trend"><h3>{title}</h3><TimeSeriesChart title={title} unit={unit} points={points} threshold={threshold} percent={unit === "%"} /></article>;
}

export function EquipmentTrends({ readings }: { readings: EquipmentReading[] }) {
  const latest = readings[readings.length - 1];
  const riskPoints = readings.map(r => ({ time: Date.parse(String(r.telemetry.timestamp ?? r.received_at)), value: r.prediction ? r.prediction.failure_probability * 100 : null, source: typeof r.telemetry.provenance === "string" ? r.telemetry.provenance : undefined }));
  const riskThresholds = new Set(readings.flatMap(r => r.prediction && Number.isFinite(r.prediction.threshold) ? [r.prediction.threshold] : []));
  const riskThreshold = riskThresholds.size === 1 ? [...riskThresholds][0] * 100 : undefined;
  return <section className="panel monitoring-panel"><div className="panel-header"><h3>Sensor history</h3><span>{readings.length} recorded readings · timestamp axis</span></div><p className="monitoring-context">These are persisted readings, updated by live events. Sensor failure limits are not exposed by this API; the model evaluates overall failure probability.</p>{latest && !latest.prediction && riskPoints.some(point => point.value !== null) && <p className="notice">The latest reading is unscored. The risk chart ends at the most recent evaluated reading.</p>}{riskThresholds.size > 1 && <p className="notice">Historical evaluations used different failure thresholds; a single threshold line is not shown.</p>}<p className="monitoring-context">Lines connect recorded samples; missing values break the line. No readings or model evaluations are estimated.</p><div className="trend-grid">{metrics.map(metric => {
    const canonical = readings.some(r => typeof r.telemetry[metric.key] === "number");
    const key = canonical ? metric.key : metric.legacy ?? metric.key;
    const points = readings.map(r => ({ time: Date.parse(String(r.telemetry.timestamp ?? r.received_at)), value: typeof r.telemetry[key] === "number" ? Number(r.telemetry[key]) : null, source: typeof r.telemetry.provenance === "string" ? r.telemetry.provenance : undefined }));
    return <Trend key={metric.key} title={metric.label} unit={canonical ? metric.unit : "(reported units)"} points={points} />;
  })}<Trend title="Failure probability" unit="%" points={riskPoints} threshold={riskThreshold} /></div></section>;
}
