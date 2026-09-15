"use client";

import { useState } from "react";
import Link from "./navigation-link";
import { Icon, type IconName } from "./ui";
import { formatTimestamp } from "@/lib/presentation";
import { workspacePath } from "@/lib/workspace";
import { summarizeWindows, reportCsv, type ReportWindow } from "@/lib/report-data";
import type { EquipmentReading, ExecutiveSummary, RecentAlert, UserRole } from "@/lib/api";

const fmt = (n: number) => n.toLocaleString("en", { maximumFractionDigits: 1 });
function Heading({ icon, title, description }: { icon: IconName; title: string; description: string }) {
  return <div className="report-panel-title"><Icon name={icon} /><div><h2>{title}</h2><p>{description}</p></div></div>;
}

export function ReportsWorkspace({ role, summary, equipment, monitoringAvailable, alerts, alertsAvailable, records, notices, asOf }: {
  role: UserRole; summary: ExecutiveSummary | null; equipment: EquipmentReading[]; monitoringAvailable: boolean;
  alerts: RecentAlert[]; alertsAvailable: boolean; records: ReportWindow[]; notices: string[]; asOf: number;
}) {
  const [days, setDays] = useState(30);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [exportStatus, setExportStatus] = useState("");
  const report = summarizeWindows(records, days, asOf);
  const filtered = report.rows.filter(row => `${row.id} ${row.equipment_id} ${row.station} ${row.work_order_id ?? ""}`.toLowerCase().includes(query.toLowerCase()));
  const current = Math.min(page, Math.max(1, Math.ceil(filtered.length / 10)));
  const max = Math.max(...report.daily.map(day => day.minutes), 1);
  const openCount = report.rows.filter(row => !row.ended_at).length;
  const closedCount = report.rows.length - openCount;
  const openShare = report.rows.length ? openCount / report.rows.length * 100 : 0;
  const total = report.rows.reduce((sum, row) => sum + row.period_minutes, 0);
  const activeDay = report.daily.find(day => day.time === selectedDay);
  const warnings = [...notices, ...(report.omitted ? [`${report.omitted} records lack valid duration or timestamps and are excluded.`] : [])];
  const exportReport = () => {
    const csv = reportCsv(report.rows, [
      ["Generated UTC", new Date(asOf).toISOString()], ["Period start UTC", new Date(report.start).toISOString()],
      ["Period end UTC", new Date(asOf).toISOString()], ["Coverage", "Accessible equipment discovered from monitoring and work orders; not a guaranteed complete network inventory"],
      ["Data status", warnings.join(" ") || "All requested sources returned successfully"],
      ["Period downtime minutes", total], ["All-time network downtime minutes", summary?.downtime_minutes ?? "Not supplied"],
      ["All-time open windows", summary?.open_windows ?? "Not supplied"], ["All-time completed windows", summary?.completed_windows ?? "Not supplied"],
      ["Network availability", "Not supplied"], ["Cause categories", "Not supplied; alert identifiers are included where returned"],
      ["Provenance note", "Provenance describes the latest equipment reading, not the downtime cause"],
    ]);
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = `maintainnexus-report-${days}days-${new Date(asOf).toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    setExportStatus(`Exported ${report.rows.length} records for the selected period.`);
  };
  return <main className="reports-workspace">
    <header className="reports-header"><div><p className="report-breadcrumb">Reports › Network Performance</p><h1>Network Outcomes</h1><p>Persisted downtime windows and backend-reported outcomes across the network.</p></div><div className="report-tools"><nav aria-label="Report links"><Link href={workspacePath(role)}>{role === "supervisor" ? "Supervisor workspace" : "Executive workspace"}</Link><Link href="/equipment">Equipment monitoring</Link><Link href="/audit">Audit records</Link></nav><div><label className="report-period"><Icon name="clock" /><select aria-label="Report period" value={days} onChange={event => { setDays(Number(event.target.value)); setPage(1); setSelectedDay(null); }}>{[7, 30, 90].map(value => <option value={value} key={value}>Last {value} days</option>)}</select></label><button className="report-export" onClick={exportReport} type="button">↓ Export Report</button></div></div></header>
    {warnings.map(message => <p className="notice" role="status" key={message}>{message}</p>)}
    <section className="report-kpis" aria-label="All-time network summary">{[
      { title: "Recorded downtime", value: summary?.downtime_minutes == null ? "—" : `${fmt(summary.downtime_minutes)}m`, detail: "All-time dispatch-to-completion windows, including open windows.", icon: "clock" as const },
      { title: "Open downtime windows", value: summary?.open_windows ?? "—", detail: "Current network windows without a recorded end time.", icon: "orders" as const },
      { title: "Completed downtime windows", value: summary?.completed_windows ?? "—", detail: "All-time network windows with a recorded end time.", icon: "approvals" as const },
      { title: "Network availability", value: "—", detail: "Measured availability is not supplied by the backend.", icon: "monitoring" as const },
    ].map(card => <article key={card.title}><span className="report-kpi-icon"><Icon name={card.icon} /></span><div><h2>{card.title}</h2><strong>{card.value}</strong><p>{card.detail}</p></div></article>)}</section>
    <p className="report-coverage">Summary cards are all-time network totals. Charts and records cover the last {days} UTC calendar days, including today, for discovered accessible equipment. Concurrent equipment windows are summed. {equipment.some(row => row.telemetry.provenance === "SYNTHETIC_LIVE_SIMULATION") && "Includes equipment with backend simulation readings."}</p>
    <section className="report-charts">
      <article className="report-panel report-trend"><Heading icon="reports" title="Downtime Trend" description="Recorded downtime minutes per UTC day" />{report.rows.length ? <><svg className="report-downtime-chart" viewBox="0 0 540 220" role="group" aria-label="Daily downtime; focus a bar to inspect its value">{[0, 1, 2, 3, 4].map(tick => <g key={tick}><line x1="44" x2="525" y1={180 - tick * 38} y2={180 - tick * 38} className="report-grid-line" /><text x="36" y={184 - tick * 38} textAnchor="end">{fmt(max * tick / 4)}</text></g>)}{report.daily.map((day, i) => <g key={day.time}><rect x={48 + i * 475 / days} y={180 - day.minutes / max * 152} width={Math.max(2, 475 / days - 3)} height={day.minutes > 0 ? Math.max(1, day.minutes / max * 152) : 0} tabIndex={0} role="button" aria-label={`${new Date(day.time).toISOString().slice(0, 10)}: ${fmt(day.minutes)} minutes`} onFocus={() => setSelectedDay(day.time)} onPointerEnter={() => setSelectedDay(day.time)} onClick={() => setSelectedDay(day.time)} onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelectedDay(day.time); } }}><title>{`${new Date(day.time).toISOString().slice(0, 10)}: ${fmt(day.minutes)} minutes`}</title></rect>{i % Math.ceil(days / 6) === 0 && <text x={48 + i * 475 / days} y="204">{new Date(day.time).toISOString().slice(5, 10)}</text>}</g>)}</svg><p className="report-chart-readout">{activeDay ? `${new Date(activeDay.time).toISOString().slice(0, 10)} · ${fmt(activeDay.minutes)} minutes` : `${fmt(total)} minutes across returned windows`}</p></> : <p className="report-empty">No usable downtime records in this period.</p>}</article>
      <article className="report-panel"><Heading icon="equipment" title="Downtime by Site" description="Selected-period minutes, grouped by supplied station" /><div className="report-sites">{report.sites.length ? report.sites.map(([site, minutes]) => <div key={site}><span>{site}</span><meter min={0} max={Math.max(...report.sites.map(([, n]) => n), 1)} value={minutes} aria-label={`${site}: ${fmt(minutes)} minutes`} /><b>{fmt(minutes)}m</b></div>) : <p className="report-empty">No site breakdown available.</p>}</div></article>
      <article className="report-panel"><Heading icon="orders" title="Downtime Window Status" description="Recorded windows overlapping the selected period" />{report.rows.length ? <div className="report-cause"><svg className="report-status-chart" viewBox="0 0 180 180" role="img" aria-label={`${openCount} open and ${closedCount} closed downtime windows`}><circle cx="90" cy="90" r="65" fill="none" stroke="#08a06b" strokeWidth="26" /><circle cx="90" cy="90" r="65" fill="none" stroke="#cf0026" strokeWidth="26" pathLength="100" strokeDasharray={`${openShare} ${100 - openShare}`} transform="rotate(-90 90 90)" /><text x="90" y="88" textAnchor="middle" className="report-donut-value">{report.rows.length}</text><text x="90" y="109" textAnchor="middle" className="report-donut-label">Windows</text></svg><dl className="report-donut-legend"><div><dt><i />Open</dt><dd>{openCount} ? {fmt(openShare)}%</dd></div><div><dt><i />Closed</dt><dd>{closedCount} ? {fmt(100 - openShare)}%</dd></div></dl></div> : <p className="report-empty">No recorded windows in this period.</p>}<p className="report-coverage">Cause categories are unavailable; this chart shows recorded window status.</p></article>
    </section>
    <div className="report-bottom"><div className="report-main-column">
      <section className="report-panel"><header className="report-section-heading"><Heading icon="equipment" title="Current Equipment State" description="Latest recorded evaluations; unscored equipment has unknown health." /><Link href="/equipment">View All Equipment →</Link></header><div className="report-states">{[
        ["NORMAL", "Normal", "approvals"], ["APPROACHING_THRESHOLD", "Needs Attention", "alerts"], ["FAILURE_DETECTED", "Failure Risk", "alerts"], ["UNSCORED", "Unscored", "equipment"],
      ].map(([state, label, icon]) => { const count = equipment.filter(row => row.state === state).length; return <article key={state} data-state={state}><Icon name={icon as IconName} /><div><span>{label}</span><strong>{monitoringAvailable ? count : "—"}</strong><small>{monitoringAvailable && equipment.length ? `${Math.round(count / equipment.length * 100)}% of returned assets` : "No equipment data"}</small></div></article>; })}</div></section>
      <section className="report-panel report-records"><Heading icon="orders" title="Network Downtime Records" description="Returned windows overlapping the selected period. Durations are clipped to that period." /><label className="report-search">Filter records<input type="search" value={query} placeholder="Equipment, station, work order or ID" onChange={event => { setQuery(event.target.value); setPage(1); }} /></label><div className="report-table-scroll"><table><thead><tr>{["ID", "Equipment", "Site", "Cause alert ID", "Start (UTC)", "End (UTC)", "Duration (m)", "Status", "Actions"].map(title => <th key={title}>{title}</th>)}</tr></thead><tbody>{filtered.slice((current - 1) * 10, current * 10).map(row => <tr key={`${row.equipment_id}-${row.id}`}><td>{row.id}</td><td>{row.equipment_id}</td><td>{row.station}</td><td>{row.cause_alert_id ?? "Not supplied"}</td><td>{formatTimestamp(row.started_at)}</td><td>{row.ended_at ? formatTimestamp(row.ended_at) : "—"}</td><td>{fmt(row.period_minutes)}</td><td><span className={`report-status ${row.ended_at ? "closed" : "open"}`}>{row.ended_at ? "Closed" : "Open"}</span></td><td><Link href={row.work_order_id ? `/work-orders/${encodeURIComponent(row.work_order_id)}` : `/equipment/${encodeURIComponent(row.equipment_id)}`}>View</Link></td></tr>)}</tbody></table></div>{!filtered.length && <p className="report-empty">No returned records match this period and filter.</p>}<footer className="report-pagination"><span>{filtered.length} records · Page {current} of {Math.max(1, Math.ceil(filtered.length / 10))}</span><button type="button" disabled={current === 1} onClick={() => setPage(current - 1)}>Previous</button><button type="button" disabled={current * 10 >= filtered.length} onClick={() => setPage(current + 1)}>Next</button></footer></section>
    </div><aside className="report-side-column"><section className="report-panel"><header className="report-section-heading"><Heading icon="alerts" title="Recent Alerts" description="Latest returned alerts" /><Link href="/alerts">View All →</Link></header>{alertsAvailable ? alerts.length ? alerts.slice(0, 4).map((alert, i) => <Link className="report-alert" key={alert.task_id ?? i} href={`/equipment/${encodeURIComponent(alert.equipment_id)}`}><Icon name="alerts" /><div><strong>{alert.failure_code?.replaceAll("_", " ") ?? "Maintenance alert"}</strong><span>{alert.equipment_id} · {alert.station_id ?? "Station not supplied"}</span><small>{formatTimestamp(alert.received_at)}</small></div></Link>) : <p className="report-empty">No alerts returned.</p> : <p className="report-empty">Alerts unavailable.</p>}</section><section className="report-panel"><Heading icon="reports" title="Quick Actions" description="Export the selected period or print this view" /><div className="report-quick-actions"><button onClick={exportReport} type="button">↓ Export to CSV</button><button onClick={() => window.print()} type="button">Print / Save PDF</button></div><p className="report-coverage">CSV includes all {report.rows.length} period records, regardless of the table search, plus coverage notes. Scheduling and custom report generation are not supported.</p><p role="status">{exportStatus}</p></section></aside></div>
    <p className="report-asof">Snapshot: {formatTimestamp(asOf)} · Refreshed by backend live events</p>
  </main>;
}
