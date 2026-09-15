"use client";

import "./equipment-alerts.css";

import { useEffect, useId, useRef, useState } from "react";
function ReceivedTime({ value }: { value?: string }) {
  const date = value ? new Date(value) : null;
  if (!date || !Number.isFinite(date.getTime())) return <span>Not supplied</span>;
  return <time dateTime={date.toISOString()}><span className="alert-received">{date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" })}</span><small>{date.toISOString().slice(11,16)} UTC</small></time>;
}

import Link from "./navigation-link";
import { AlertEvidence } from "./alert-evidence";
import { StatusBadge } from "./ui";
import { TablePagination } from "./table-pagination";
import type { RecentAlert, Technician, WorkOrder } from "@/lib/api";

const identity = (alert: RecentAlert) => alert.task_id ?? JSON.stringify([alert.equipment_id, alert.received_at, alert.failure_code, alert.telemetry?.timestamp]);
const timestamp = (alert: RecentAlert) => {
  const time = Date.parse(alert.received_at ?? "");
  return Number.isFinite(time) ? time : -Infinity;
};
function AlertDrawer({ alert, orders, technicians, allowAssignment, ordersAvailable, onClose }: {
  alert: RecentAlert; orders: WorkOrder[]; technicians?: Technician[]; allowAssignment: boolean; ordersAvailable: boolean; onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const title = useId();
  useEffect(() => {
    const dialog = ref.current;
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    dialog?.showModal();
    document.body.style.overflow = "hidden";
    return () => { dialog?.close(); document.body.style.overflow = overflow; previous?.focus(); };
  }, []);
  return <dialog className="alert-detail-drawer" ref={ref} aria-labelledby={title} onCancel={event => { event.preventDefault(); onClose(); }}>
    <header><div><span className="eyebrow">ALERT DETAILS</span><h2 id={title}>{alert.equipment_id}</h2></div><button type="button" onClick={onClose} autoFocus aria-label="Close alert details">Close</button></header>
    {alert.telemetry?.provenance && <p className="chart-source">Source: {alert.telemetry.provenance}</p>}
    <AlertEvidence alerts={[alert]} orders={orders} technicians={technicians} allowAssignment={allowAssignment} ordersAvailable={ordersAvailable} />
  </dialog>;
}

export function EquipmentAlerts({ alerts, orders, technicians, allowAssignment = false, ordersAvailable = true, hideEquipment = false }: {
  alerts: RecentAlert[]; orders: WorkOrder[]; technicians?: Technician[]; allowAssignment?: boolean; ordersAvailable?: boolean; hideEquipment?: boolean;
}) {
  const [accepted, setAccepted] = useState(() => alerts.toSorted((a, b) => timestamp(b) - timestamp(a)));
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("");
  const [linkage, setLinkage] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selected, setSelected] = useState<string | null>(null);
  const latest = new Map(alerts.map(alert => [identity(alert), alert]));
  const acceptedIds = new Set(accepted.map(identity));
  const incoming = alerts.filter(alert => !acceptedIds.has(identity(alert))).length;
  const rows = accepted.map(alert => latest.get(identity(alert)) ?? alert);
  const findOrder = (alert: RecentAlert) => alert.task_id ? orders.find(order => order.alert_task_id === alert.task_id) : undefined;
  const filtered = rows.filter(alert => {
    const match = `${alert.equipment_id} ${alert.task_id ?? ""} ${alert.failure_code ?? ""}`.toLowerCase().includes(query.toLowerCase());
    return match && (!severity || (alert.severity ?? "NOT_SUPPLIED") === severity) && (!linkage || (ordersAvailable && (linkage === "linked" ? !!findOrder(alert) : !findOrder(alert))));
  });
  const current = Math.min(page, Math.max(1, Math.ceil(filtered.length / pageSize)));
  const chosen = selected ? latest.get(selected) ?? rows.find(alert => identity(alert) === selected) : undefined;
  return <section className="panel monitoring-panel maintenance-alert-browser">
    <div className="panel-header"><div><h3>Equipment maintenance activity</h3></div></div>
    <p className="monitoring-context">Newest first. Search and pagination cover returned records, not the complete alert history.</p>
    {incoming > 0 && <button className="new-alerts-button" type="button" onClick={() => { setAccepted(alerts.toSorted((a, b) => timestamp(b) - timestamp(a))); setPage(1); }}>{incoming} new alerts available - show latest</button>}
    <div className="filter-bar alert-browser-filters">
      <label>Search alerts<input type="search" placeholder="Equipment, alert ID or failure code" value={query} onChange={event => { setQuery(event.target.value); setPage(1); }} /></label>
      <label>Severity<select value={severity} onChange={event => { setSeverity(event.target.value); setPage(1); }}><option value="">All severities</option>{[...new Set(rows.map(alert => alert.severity ?? "NOT_SUPPLIED"))].sort().map(value => <option key={value} value={value}>{value === "NOT_SUPPLIED" ? "Not supplied" : value}</option>)}</select></label>
      <label>Maintenance<select value={linkage} disabled={!ordersAvailable} onChange={event => { setLinkage(event.target.value); setPage(1); }}><option value="">All alerts</option><option value="linked">Linked work order</option><option value="unlinked">No linked task returned</option></select></label>
      <label>Per page<select value={pageSize} onChange={event => { setPageSize(Number(event.target.value)); setPage(1); }}>{[10,25,50].map(size => <option key={size}>{size}</option>)}</select></label>
      {(query || severity || linkage) && <button type="button" onClick={() => { setQuery(""); setSeverity(""); setLinkage(""); setPage(1); }}>Reset filters</button>}
    </div>
    {!ordersAvailable && <p className="notice">Maintenance linkage unavailable. Task status cannot be confirmed.</p>}
    {filtered.length > 0 && <div className="alert-browser-scroll"><table className="alert-browser-table"><caption className="sr-only">Recorded equipment alerts and linked maintenance</caption><colgroup><col className="received-col" />{!hideEquipment && <col className="equipment-col" />}<col className="alert-col" /><col className="severity-col" /><col className="maintenance-col" /><col className="action-col" /></colgroup><thead><tr><th scope="col">Received (UTC)</th>{!hideEquipment && <th scope="col">Equipment</th>}<th scope="col">Alert</th><th scope="col">Severity</th><th scope="col">Maintenance</th><th scope="col">Action</th></tr></thead><tbody>{filtered.slice((current - 1) * pageSize, current * pageSize).map((alert, index) => {
      const order = findOrder(alert);
      return <tr key={`${identity(alert)}-${index}`}><td data-label="Received"><ReceivedTime value={alert.received_at} /></td>{!hideEquipment && <td data-label="Equipment"><Link href={`/equipment/${encodeURIComponent(alert.equipment_id)}`}>{alert.equipment_id}</Link></td>}<td data-label="Alert"><span className="alert-code" title={alert.failure_code ?? "Maintenance alert"}>{alert.failure_code?.replaceAll("_", " ") ?? "Maintenance alert"}</span>{alert.telemetry?.provenance === "SYNTHETIC_LIVE_SIMULATION" && <small className="alert-simulation-label">Simulation</small>}</td><td data-label="Severity"><StatusBadge status={alert.severity} /></td><td data-label="Maintenance">{!ordersAvailable ? <span className="alert-neutral">Linkage unavailable</span> : order ? <Link href={`/work-orders/${encodeURIComponent(order.work_order_id)}`}><StatusBadge status={order.status} /></Link> : <span className="alert-neutral">No linked task returned</span>}</td><td data-label="Action"><button type="button" onClick={() => setSelected(identity(alert))} aria-label={`View details for ${alert.failure_code ?? "alert"} on ${alert.equipment_id}`}>View details</button></td></tr>;
    })}</tbody></table></div>}
    {!filtered.length && <div className="empty-state"><h4>No records found</h4><p>{rows.length ? "No equipment-related maintenance alerts match the current filters." : "No equipment-related maintenance alerts returned."}</p></div>}
    <TablePagination page={current} total={filtered.length} pageSize={pageSize} onChange={setPage} />
    {chosen && <AlertDrawer alert={chosen} orders={orders} technicians={technicians} allowAssignment={allowAssignment && latest.has(identity(chosen))} ordersAvailable={ordersAvailable} onClose={() => setSelected(null)} />}
  </section>;
}
