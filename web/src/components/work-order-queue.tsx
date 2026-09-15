"use client";
import { useState } from "react";
import { formatTimestamp } from "@/lib/presentation";
import Link from "@/components/navigation-link";
import { ActionButton } from "./action-button";
import { WorkOrderDetail } from "./work-order-detail";
import { StatusBadge } from "./ui";
import { TablePagination } from "./table-pagination";
import type { WorkOrder } from "@/lib/api";
export function WorkOrderQueue({
  orders,
  status,
  supervisor,
}: {
  orders: WorkOrder[];
  status: string;
  supervisor: boolean;
}) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const filtered = orders.filter(
    (order) =>
      (!status || order.status === status) &&
      `${order.work_order_id} ${order.equipment_id} ${order.assigned_technician_id ?? ""}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const current = Math.min(page, Math.max(1, Math.ceil(filtered.length / 10)));
  const statuses = Array.from(
    new Set([
      "PENDING_APPROVAL",
      "ESCALATED",
      ...orders
        .map((order) => order.status)
        .filter((s): s is string => Boolean(s)),
    ]),
  );
  return (
    <>
      <form className="filter-bar" method="GET">
        <label>
          Search work orders
          <input
            type="search"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(1);
            }}
            placeholder="ID, equipment or technician"
          />
        </label>
        <label>
          Status
          <select name="status" defaultValue={status}>
            <option value="">All statuses</option>
            {statuses.map((value) => (
              <option key={value} value={value}>
                {value.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </label>
        <button type="submit">Apply filter</button>
        <Link href="?status=">Clear</Link>
      </form>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Work order</th>
              <th scope="col">Equipment</th>
              <th scope="col" className="secondary-column">
                Assigned to / Part
              </th>
              <th scope="col">Status</th>
              <th scope="col" className="secondary-column">
                Created
              </th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice((current - 1) * 10, current * 10).map((order) => (
              <tr key={order.work_order_id}>
                <td>
                  <Link
                    href={`/work-orders/${encodeURIComponent(order.work_order_id)}`}
                  >
                    {order.work_order_id}
                  </Link>
                  <WorkOrderDetail id={order.work_order_id} />
                </td>
                <td>
                  <Link
                    href={`/equipment/${encodeURIComponent(order.equipment_id)}`}
                  >
                    {order.equipment_id}
                  </Link>
                  {order.risk_drivers?.length ? (
                    <details>
                      <summary>Why flagged</summary>
                      {order.risk_drivers.map((driver) => (
                        <p key={driver.feature}>
                          {driver.feature}: {driver.reason}
                        </p>
                      ))}
                    </details>
                  ) : null}
                </td>
                <td className="secondary-column">
                  {order.assigned_technician_id ?? "Not supplied"}
                  <small>{order.reserved_part ?? "Part not supplied"}</small>
                </td>
                <td>
                  <StatusBadge status={order.status} />
                </td>
                <td className="secondary-column">
                  {order.created_at
                    ? formatTimestamp(order.created_at)
                    : "Not supplied"}
                </td>
                <td>
                  {order.status === "PENDING_APPROVAL" ||
                  order.status === "ESCALATED" ? (
                    <div className="row-actions">
                      <ActionButton
                        action="approve"
                        workOrderId={order.work_order_id}
                      />
                      <ActionButton
                        action="reject"
                        workOrderId={order.work_order_id}
                      />
                      {supervisor && order.status === "PENDING_APPROVAL" && (
                        <ActionButton
                          action="escalate"
                          workOrderId={order.work_order_id}
                        />
                      )}
                    </div>
                  ) : (
                    <span className="resolved-label">
                      No review action needed
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!filtered.length && (
        <p className="empty-state">No work orders match this filter.</p>
      )}
      <TablePagination
        total={filtered.length}
        page={current}
        onChange={setPage}
      />
    </>
  );
}
