"use client";
import { useState } from "react";
import { formatTimestamp } from "@/lib/presentation";
import Link from "./navigation-link";
import { TablePagination } from "./table-pagination";
import type { EquipmentReading, Thresholds } from "@/lib/api";
export function EquipmentState({ state }: { state: string }) {
  const labels: Record<string, string> = {
    NORMAL: "Normal",
    APPROACHING_THRESHOLD: "Approaching threshold",
    FAILURE_DETECTED: "Failure risk detected",
    UNSCORED: "Unscored",
  };
  return (
    <span className={`equipment-state state-${state.toLowerCase()}`}>
      {labels[state] ?? state}
    </span>
  );
}
export function EquipmentMonitor({
  equipment,
  thresholds,
  filtered = false,
}: {
  equipment: EquipmentReading[];
  thresholds: Thresholds;
  filtered?: boolean;
}) {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [page, setPage] = useState(1);
  const rows = equipment.filter(
    (row) =>
      (!type || row.telemetry.asset_type === type) &&
      `${row.equipment_id} ${row.station_id ?? ""} ${row.telemetry.asset_type ?? ""}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const current = Math.min(page, Math.max(1, Math.ceil(rows.length / 10)));
  return (
    <section className="panel monitoring-panel">
      <div className="panel-header">
        <div>
          <h3>Equipment Overview</h3>
          <span>Current readings in your accessible station scope</span>
        </div>
        <Link href="/monitoring">Live monitoring →</Link>
      </div>
      <p className="monitoring-context">
        Failure threshold: {(thresholds.failure_probability * 100).toFixed(1)}%
        over {thresholds.prediction_horizon_hours} hours.{" "}
        {thresholds.warning_probability === null
          ? "Warning threshold is not configured."
          : `Warning threshold: ${(thresholds.warning_probability * 100).toFixed(1)}%.`}
      </p>
      <div className="filter-bar">
        <label>
          Search equipment
          <input
            type="search"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(1);
            }}
            placeholder="Equipment, station or type"
          />
        </label>
        <label>
          Equipment type
          <select
            value={type}
            onChange={(event) => {
              setType(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All types</option>
            {Array.from(
              new Set(
                equipment
                  .map((row) => row.telemetry.asset_type)
                  .filter(Boolean),
              ),
            ).map((value) => (
              <option key={String(value)}>{String(value)}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">State</th>
              <th scope="col">Equipment</th>
              <th scope="col" className="secondary-column">
                Type / Station
              </th>
              <th scope="col">Key readings</th>
              <th scope="col">Failure probability</th>
              <th scope="col" className="secondary-column">
                Sensor timestamp
              </th>
              <th scope="col">Details</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice((current - 1) * 10, current * 10).map((row) => (
              <tr key={row.equipment_id}>
                <td>
                  <EquipmentState state={row.state} />
                </td>
                <td>
                  <Link
                    href={`/equipment/${encodeURIComponent(row.equipment_id)}`}
                  >
                    {row.equipment_id}
                  </Link>
                  {row.telemetry.provenance === "SYNTHETIC_LIVE_SIMULATION" && (
                    <small>Synthetic simulation</small>
                  )}
                </td>
                <td className="secondary-column">
                  {row.telemetry.asset_type ?? "Not supplied"}
                  <small>{row.station_id ?? "Station not supplied"}</small>
                </td>
                <td>
                  Vibration{" "}
                  {row.telemetry.vibration_mm_s ??
                    row.telemetry.vibration ??
                    "—"}
                  {row.telemetry.vibration_mm_s != null
                    ? " mm/s"
                    : " (reported units)"}
                  <small>
                    Temperature{" "}
                    {row.telemetry.temperature_c ??
                      row.telemetry.temperature ??
                      "—"}
                    {row.telemetry.temperature_c != null
                      ? " °C"
                      : " (reported units)"}
                  </small>
                </td>
                <td>
                  {row.prediction
                    ? `${(row.prediction.failure_probability * 100).toFixed(1)}%`
                    : "Unscored"}
                  {row.evaluation_reason && (
                    <details>
                      <summary>Why unscored?</summary>
                      <p>{row.evaluation_reason}</p>
                    </details>
                  )}
                </td>
                <td className="secondary-column">
                  {row.telemetry.timestamp
                    ? formatTimestamp(String(row.telemetry.timestamp))
                    : "Not supplied"}
                </td>
                <td>
                  <Link
                    href={`/equipment/${encodeURIComponent(row.equipment_id)}`}
                  >
                    View →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!rows.length && (
        <p className="empty-state">
          {filtered
            ? "No equipment matches this state filter."
            : query || type
              ? "No equipment matches these filters."
              : "No equipment telemetry recorded in your accessible scope."}
        </p>
      )}
      <TablePagination page={current} total={rows.length} onChange={setPage} />
    </section>
  );
}
