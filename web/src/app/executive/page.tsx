import Link from "@/components/navigation-link";
import { ApiNotice } from "@/components/api-notice";
import { getExecutiveSummary } from "@/lib/api";
import { requireSession } from "@/lib/session";
import { LiveUpdates } from "@/components/live-updates";
import { LogoutButton } from "@/components/logout-button";

export default async function ExecutivePage() {
  const { token, user } = await requireSession(["executive", "supervisor"]);
  const result = await getExecutiveSummary(token);
  const summary = result.data;
  const trend = Array.isArray(summary?.uptime_trend) ? summary.uptime_trend : [];
  return <main className="executive-shell">
    <header className="executive-header"><div><span className="eyebrow">EXECUTIVE / RECORDED MAINTENANCE</span><h1>Maintenance outcomes</h1><p>Persisted downtime windows and backend-reported outcomes across the network.</p></div><div className="executive-actions">{user.role === "supervisor" && <Link href="/dashboard">Supervisor workspace</Link>}<Link href="/equipment">Equipment monitoring</Link><Link href="/audit">Audit records</Link><LiveUpdates /><LogoutButton /></div></header>
    <ApiNotice result={result} label="Executive summary unavailable" />
    <section className="executive-cards">
      <article><span>Recorded downtime</span><strong>{summary?.downtime_minutes === undefined ? "—" : `${summary.downtime_minutes}m`}</strong><small>Accumulated dispatch-to-completion windows, including open windows</small></article>
      <article><span>Open downtime windows</span><strong>{summary?.open_windows ?? "—"}</strong><small>Dispatched maintenance without a closed downtime window</small></article>
      <article><span>Completed downtime windows</span><strong>{summary?.completed_windows ?? "—"}</strong><small>{summary?.downtime_windows === undefined ? "Total windows not supplied" : `${summary.downtime_windows} total recorded windows`}</small></article>
    </section>
    {typeof summary?.uptime_trend === "string" && <section className="executive-panel"><h2>Backend downtime indicator</h2><strong>{summary.uptime_trend.replaceAll("_", " ")}</strong><p>The backend derives this indicator from accumulated downtime. It is not a measured uptime percentage or a dated uptime trend.</p></section>}
    {(summary?.downtime_avoided_minutes !== undefined || summary?.cost_saved !== undefined) && <section className="executive-panel"><h2>Additional backend outcomes</h2>{summary.downtime_avoided_minutes !== undefined && <p>Downtime avoided: <strong>{`${summary.downtime_avoided_minutes}m`}</strong></p>}{summary.cost_saved !== undefined && <p>Cost saved: <strong>{summary.cost_saved.toLocaleString()}</strong> (currency not supplied)</p>}</section>}
    {summary && summary.downtime_avoided_minutes === undefined && summary.cost_saved === undefined && <p className="monitoring-context">The current backend does not calculate avoided downtime or cost savings. Recorded downtime is not a savings estimate.</p>}
    <section className="executive-panel"><h2>Uptime history</h2>{trend.length ? <figure><svg className="uptime-chart" viewBox="0 0 600 150" role="img" aria-label="Backend-reported uptime over time"><polyline fill="none" stroke="currentColor" strokeWidth="3" points={trend.map((point, index) => `${trend.length === 1 ? 300 : 20 + index / (trend.length - 1) * 560},${130 - Math.max(0, Math.min(100, point.uptime)) / 100 * 110}`).join(" ")} />{trend.map((point, index) => <circle key={`${point.date}-${index}`} cx={trend.length === 1 ? 300 : 20 + index / (trend.length - 1) * 560} cy={130 - Math.max(0, Math.min(100, point.uptime)) / 100 * 110} r="4"><title>{point.date}: {point.uptime}%</title></circle>)}</svg><figcaption>Uptime percentage, 0–100%</figcaption><table><thead><tr><th>Date</th><th>Uptime</th></tr></thead><tbody>{trend.map((point, index) => <tr key={`${point.date}-${index}`}><td>{point.date}</td><td>{point.uptime}%</td></tr>)}</tbody></table></figure> : <p className="executive-empty">The backend has not supplied a dated uptime series yet.</p>}</section>
    <section className="executive-panel"><span className="eyebrow">STATION COMPARISON</span><h2>Operational reliability</h2>{summary?.station_comparison?.length ? <div className="station-list">{summary.station_comparison.map(station => <div key={station.station_id}><span>{station.station_id}</span><b>{station.uptime}%</b><i><em style={{ width: `${Math.max(0, Math.min(100, station.uptime))}%` }} /></i></div>)}</div> : <p className="executive-empty">No station comparison data supplied yet.</p>}</section>
  </main>;
}
