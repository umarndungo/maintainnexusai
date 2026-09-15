"use client";
import { useState } from "react";
import { formatTimestamp } from "@/lib/presentation";
import Link from "./navigation-link";
import { EquipmentAlerts } from "./equipment-alerts";
import { StatusBadge } from "./ui";
import { TablePagination } from "./table-pagination";
import type { RecentAlert, Technician, WorkOrder } from "@/lib/api";
export function AlertsTable({
  alerts,
  orders,
  technicians,
  allowAssignment,
  ordersAvailable,
}: {
  alerts: RecentAlert[];
  orders: WorkOrder[];
  technicians?: Technician[];
  allowAssignment: boolean;
  ordersAvailable: boolean;
}) {
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const filtered = alerts.filter(
    (alert) =>
      (!severity || alert.severity === severity) &&
      `${alert.equipment_id} ${alert.task_id ?? ""} ${alert.failure_code ?? ""}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const current = Math.min(page, Math.max(1, Math.ceil(filtered.length / 10)));
  const detail = alerts.find((alert) => alert.task_id === selected);
  return (
    <div className={detail ? "alerts-layout" : ""}>
      <section className="panel">
        <div className="filter-bar">
          <label>
            Search alerts
            <input
              type="search"
              placeholder="Equipment, alert ID or failure code"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setPage(1);
              }}
            />
          </label>
          <label>
            Severity
            <select
              value={severity}
              onChange={(event) => {
                setSeverity(event.target.value);
                setPage(1);
              }}
            >
              <option value="">All severities</option>
              {Array.from(
                new Set(alerts.map((alert) => alert.severity).filter(Boolean)),
              ).map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>
          <button
            onClick={() => {
              setQuery("");
              setSeverity("");
              setPage(1);
            }}
            type="button"
          >
            Reset
          </button>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Raised</th>
                <th scope="col">Equipment</th>
                <th scope="col">Severity</th>
                <th scope="col" className="secondary-column">
                  Failure / probability
                </th>
                <th scope="col">Maintenance</th>
                <th scope="col">Review</th>
              </tr>
            </thead>
            <tbody>
              {filtered
                .slice((current - 1) * 10, current * 10)
                .map((alert, index) => {
                  const order = orders.find(
                    (order) => order.alert_task_id === alert.task_id,
                  );
                  return (
                    <tr key={alert.task_id ?? index}>
                      <td>
                        {alert.received_at
                          ? formatTimestamp(alert.received_at)
                          : "Not supplied"}
                      </td>
                      <td>
                        <Link
                          href={`/equipment/${encodeURIComponent(alert.equipment_id)}`}
                        >
                          {alert.equipment_id}
                        </Link>
                        <small>
                          {alert.station_id ?? "Station not supplied"}
                        </small>
                      </td>
                      <td>
                        <StatusBadge status={alert.severity} />
                      </td>
                      <td className="secondary-column">
                        {alert.failure_code?.replaceAll("_", " ") ??
                          "Not supplied"}
                        <small>
                          {alert.prediction
                            ? `${(alert.prediction.failure_probability * 100).toFixed(1)}% failure probability`
                            : "No compatible evaluation"}
                        </small>
                      </td>
                      <td>
                        {!ordersAvailable ? (
                          "Service unavailable"
                        ) : order ? (
                          <Link
                            href={`/work-orders/${encodeURIComponent(order.work_order_id)}`}
                          >
                            {order.work_order_id}
                          </Link>
                        ) : (
                          "No linked task returned"
                        )}
                      </td>
                      <td>
                        <button
                          className="table-review"
                          type="button"
                          disabled={!alert.task_id}
                          onClick={() => setSelected(alert.task_id ?? null)}
                        >
                          Review
                        </button>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
        {!filtered.length && (
          <p className="empty-state">No recorded alerts match these filters.</p>
        )}
        <TablePagination
          total={filtered.length}
          page={current}
          onChange={setPage}
        />
      </section>
      {detail && (
        <aside
          className="alert-detail-pane"
          aria-label="Selected alert details"
        >
          <div className="panel-header">
            <h3>Alert details</h3>
            <button
              className="icon-button"
              aria-label="Close alert details"
              onClick={() => setSelected(null)}
              type="button"
            >
              ×
            </button>
          </div>
          <EquipmentAlerts
            alerts={[detail]}
            orders={orders}
            technicians={technicians}
            allowAssignment={allowAssignment}
            ordersAvailable={ordersAvailable}
          />
        </aside>
      )}
    </div>
  );
}
