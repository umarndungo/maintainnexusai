import { NetworkOverview } from "@/components/network-overview";
import { formatTimestamp } from "@/lib/presentation";
import { TimeSeriesChart } from "@/components/time-series-chart";
import Link from "@/components/navigation-link";
import { ApiNotice } from "@/components/api-notice";
import { getExecutiveSummary, getMonitoring, getAuditLogs } from "@/lib/api";
import { requireSession } from "@/lib/session";
import { AppShell } from "@/components/app-shell";


export default async function ExecutivePage() {
  const { token, user } = await requireSession(["executive", "supervisor"]);
  const [result, monitoring, audit] = await Promise.all([getExecutiveSummary(token), getMonitoring(token), getAuditLogs(token)]);
  const summary = result.data;
  const trend = Array.isArray(summary?.uptime_trend) ? summary.uptime_trend : [];
  return <AppShell user={user}><main className="executive-shell">
    <header className="executive-header"><div><span className="eyebrow">EXECUTIVE / NETWORK PERFORMANCE</span><h1>Network Outcomes</h1><p>Persisted downtime windows and backend-reported outcomes across the network.</p></div><div className="executive-actions">{user.role === "supervisor" && <Link href="/supervisor">Supervisor workspace</Link>}<Link href="/equipment">Equipment monitoring</Link><Link href="/audit">Audit records</Link></div></header>
    <ApiNotice result={result} label="Executive summary unavailable" />
    <section className="executive-cards">
      <article><span>Recorded downtime</span><strong>{summary?.downtime_minutes === undefined ? "—" : `${summary.downtime_minutes}m`}</strong><small>Accumulated dispatch-to-completion windows, including open windows</small></article>
      <article><span>Open downtime windows</span><strong>{summary?.open_windows ?? "—"}</strong><small>Dispatched maintenance without a closed downtime window</small></article>
      <article><span>Completed downtime windows</span><strong>{summary?.completed_windows ?? "—"}</strong><small>{summary?.downtime_windows === undefined ? "Total windows not supplied" : `${summary.downtime_windows} total recorded windows`}</small></article>
    </section>
    <ApiNotice result={monitoring} label="Network equipment unavailable" />
    {monitoring.available && <NetworkOverview equipment={monitoring.data?.equipment ?? []} />}
    {typeof summary?.uptime_trend === "string" && <section className="executive-panel"><h2>Backend downtime indicator</h2><strong>{summary.uptime_trend.replaceAll("_", " ")}</strong><p>The backend derives this indicator from accumulated downtime. It is not a measured uptime percentage or a dated uptime trend.</p></section>}
    {(summary?.downtime_avoided_minutes !== undefined || summary?.cost_saved !== undefined) && <section className="executive-panel"><h2>Additional backend outcomes</h2>{summary.downtime_avoided_minutes !== undefined && <p>Downtime avoided: <strong>{`${summary.downtime_avoided_minutes}m`}</strong></p>}{summary.cost_saved !== undefined && <p>Cost saved: <strong>{summary.cost_saved.toLocaleString()}</strong> (currency not supplied)</p>}</section>}
    {summary && summary.downtime_avoided_minutes === undefined && summary.cost_saved === undefined && <p className="monitoring-context">The current backend does not calculate avoided downtime or cost savings. Recorded downtime is not a savings estimate.</p>}
    <section className="executive-panel"><h2>Uptime history</h2>{trend.length ? <TimeSeriesChart title="Uptime" unit="%" percent points={trend.map(point => ({ time: Date.parse(point.date), value: point.uptime }))} /> : <p className="executive-empty">The backend has not supplied a dated uptime series yet.</p>}</section>
    <section className="executive-panel"><span className="eyebrow">STATION COMPARISON</span><h2>Operational reliability</h2>{summary?.station_comparison?.length ? <div className="station-list">{summary.station_comparison.map(station => <div key={station.station_id}><span>{station.station_id}</span><b>{station.uptime}%</b><i><em style={{ width: `${Math.max(0, Math.min(100, station.uptime))}%` }} /></i></div>)}</div> : <p className="executive-empty">No station comparison data supplied yet.</p>}</section>
    <section className="executive-panel"><div className="panel-header"><div><span className="eyebrow">TRACEABILITY</span><h2>Recent recorded activity</h2></div><Link href="/audit">Explore audit records</Link></div><ApiNotice result={audit} label="Audit activity unavailable" />{audit.available && (audit.data?.length ? audit.data.slice(0, 5).map(log => <div className="executive-audit-row" key={log.id}><strong>{log.event_name.replaceAll("_", " ")}</strong><span>{formatTimestamp(log.timestamp)}</span></div>) : <p className="empty-state">No audit activity supplied.</p>)}</section>
  </main></AppShell>;
}

