import type { EquipmentReading } from "@/lib/api";

const metrics = [
  { key: "temperature_c", legacy: "temperature", label: "Temperature", unit: "°C" },
  { key: "vibration_mm_s", legacy: "vibration", label: "Vibration", unit: "mm/s" },
  { key: "pressure_bar", label: "Pressure", unit: "bar" },
  { key: "flow_rate_m3h", label: "Flow rate", unit: "m³/h" },
  { key: "motor_current_a", label: "Motor current", unit: "A" },
  { key: "valve_position_pct", label: "Valve position", unit: "%" },
];

function Trend({ title, unit, points, threshold }: { title: string; unit: string; points: Array<{ time: number; value: number }>; threshold?: number }) {
  if (!points.length) return <article className="metric-trend"><h3>{title}</h3><p className="empty-state">This metric has not been supplied.</p></article>;
  const min = Math.min(...points.map(p => p.value), threshold ?? Infinity);
  const max = Math.max(...points.map(p => p.value), threshold ?? -Infinity);
  const span = max - min || Math.max(Math.abs(max) * .1, 1);
  const first = points[0].time, last = points[points.length - 1].time;
  const x = (time: number) => 20 + (time - first) / (last - first || 1) * 460;
  const y = (value: number) => 125 - (value - min) / span * 100;
  return <article className="metric-trend"><div className="metric-trend-heading"><h3>{title}</h3><strong>{points[points.length - 1].value.toLocaleString(undefined, { maximumFractionDigits: 2 })} {unit}</strong></div>{points.length > 1 ? <svg className="sensor-chart" viewBox="0 0 500 150" role="img" aria-label={`${title}: ${points.length} recorded readings, latest ${points[points.length - 1].value} ${unit}`}><line x1="20" x2="480" y1="125" y2="125" className="chart-baseline" />{threshold !== undefined && <line x1="20" x2="480" y1={y(threshold)} y2={y(threshold)} className="chart-threshold" />}<polyline points={points.map(p => `${x(p.time)},${y(p.value)}`).join(" ")} fill="none" stroke="currentColor" strokeWidth="2" />{points.map((p, index) => <circle key={index} cx={x(p.time)} cy={y(p.value)} r="3"><title>{new Date(p.time).toLocaleString()}: {p.value} {unit}</title></circle>)}</svg> : <p>One reading recorded. A trend needs at least two readings.</p>}<div className="chart-times"><small>{new Date(first).toLocaleString()}</small><small>{new Date(last).toLocaleString()}</small></div>{threshold !== undefined && <p className="threshold-legend">Dashed line: server failure threshold {threshold.toFixed(1)}%</p>}</article>;
}

export function EquipmentTrends({ readings }: { readings: EquipmentReading[] }) {
  const latest = readings[readings.length - 1];
  const riskPoints = readings.filter(r => r.prediction).map(r => ({ time: Date.parse(String(r.telemetry.timestamp ?? r.received_at)), value: r.prediction!.failure_probability * 100 }));
  return <section className="panel monitoring-panel"><div className="panel-header"><h3>Sensor history</h3><span>{readings.length} recorded readings · timestamp axis</span></div><p className="monitoring-context">These are persisted readings, updated by live events. Sensor failure limits are not exposed by this API; the model evaluates overall failure probability.</p><div className="trend-grid">{metrics.map(metric => {
    const canonical = readings.some(r => typeof r.telemetry[metric.key] === "number");
    const key = canonical ? metric.key : metric.legacy ?? metric.key;
    const points = readings.filter(r => typeof r.telemetry[key] === "number").map(r => ({ time: Date.parse(String(r.telemetry.timestamp ?? r.received_at)), value: Number(r.telemetry[key]) }));
    return <Trend key={metric.key} title={metric.label} unit={canonical ? metric.unit : "(reported units)"} points={points} />;
  })}<Trend title="Failure probability" unit="%" points={riskPoints} threshold={latest?.prediction ? latest.prediction.threshold * 100 : undefined} /></div></section>;
}
