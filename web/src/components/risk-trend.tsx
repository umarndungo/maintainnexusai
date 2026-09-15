import type { EquipmentReading } from "@/lib/api";
import Link from "./navigation-link";
import { TimeSeriesChart } from "./time-series-chart";

export function RiskTrend({
  readings,
  equipment,
  selected,
  range = "24",
  basePath = "/dashboard",
  asOf,
}: {
  readings: EquipmentReading[];
  equipment: EquipmentReading[];
  selected?: string;
  range?: string;
  basePath?: string;
  asOf: number;
}) {
  const hours = ["1", "6", "24"].includes(range) ? Number(range) : 24;
  const points = readings.filter(
    (row) =>
      row.prediction &&
      Date.parse(String(row.telemetry.timestamp)) >= asOf - hours * 3600000,
  );
  const thresholds = new Set(points.map(row => row.prediction!.threshold).filter(Number.isFinite));
  const threshold = thresholds.size === 1 ? [...thresholds][0] * 100 : undefined;
  return (
    <section className="panel risk-trend">
      <div className="panel-header">
        <div>
          <h3>Equipment Risk Trend</h3>
          <span>
            {selected ?? "No equipment selected"} · Recorded model evaluations
          </span>
        </div>
        {selected && (
          <Link href={`/equipment/${encodeURIComponent(selected)}`}>
            View asset
          </Link>
        )}
      </div>
      <p className="monitoring-context">The API returns up to 200 recent readings. Time filters apply to that available history; gaps are not estimated.</p>
      <form className="filter-bar" action={basePath}>
        <label>
          Equipment
          <select name="equipment" defaultValue={selected}>
            {equipment.map((row) => (
              <option key={row.equipment_id}>{row.equipment_id}</option>
            ))}
          </select>
        </label>
        <label>
          Time range
          <select name="range" defaultValue={String(hours)}>
            <option value="1">Last hour</option>
            <option value="6">Last 6 hours</option>
            <option value="24">Last 24 hours</option>
          </select>
        </label>
        <button type="submit">View trend</button>
      </form>
      {points.length ? (
        <TimeSeriesChart title="Failure probability" unit="%" percent threshold={threshold} points={readings
          .filter(row => Date.parse(String(row.telemetry.timestamp)) >= asOf - hours * 3600000)
          .map(row => ({ time: Date.parse(String(row.telemetry.timestamp)), value: row.prediction ? row.prediction.failure_probability * 100 : null, source: typeof row.telemetry.provenance === "string" ? row.telemetry.provenance : undefined }))} />
      ) : (
        <p className="empty-state">
          No model evaluations recorded in this time range. Unscored readings
          are not estimated.
        </p>
      )}
      {thresholds.size > 1 && <p className="monitoring-context">Failure thresholds changed in this history; no single threshold line is shown.</p>}
    </section>
  );
}
