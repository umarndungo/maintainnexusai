import { getExecutiveSummary } from "@/lib/api";
import { cookies } from "next/headers";
import Link from "next/link";
import { LogoutButton } from "@/components/logout-button";
import { redirect } from "next/navigation";

export default async function ExecutivePage() {
  const token = (await cookies()).get("maintainnexus_token")?.value;
  if (!token) redirect("/login");
  const result = await getExecutiveSummary(token);
  const summary = result.data;

  return <main className="executive-shell"><header className="executive-header"><div><span className="eyebrow">VALUE COMMAND / EXECUTIVE</span><h1>Maintenance impact</h1><p>Backend-computed outcomes across the operating network.</p></div><div className="executive-actions"><Link href="/dashboard">Engineer view -&gt;</Link><LogoutButton /></div></header><section className="executive-cards"><article><span>Downtime avoided</span><strong>{summary?.downtime_avoided_minutes === undefined ? "--" : `${summary.downtime_avoided_minutes}m`}</strong><small>From persisted downtime windows</small></article><article><span>Cost saved</span><strong>{summary?.cost_saved === undefined ? "--" : `$${summary.cost_saved.toLocaleString()}`}</strong><small>Backend aggregation</small></article><article><span>Uptime trend</span><strong>{summary?.uptime_trend?.length ? `${summary.uptime_trend.at(-1)?.uptime}%` : "--"}</strong><small>Current reporting period</small></article></section><section className="executive-panel"><div><span className="eyebrow">STATION COMPARISON</span><h2>Operational reliability</h2></div>{summary?.station_comparison?.length ? <div className="station-list">{summary.station_comparison.map((station) => <div key={station.station_id}><span>{station.station_id}</span><b>{station.uptime}%</b><i><em style={{ width: `${station.uptime}%` }} /></i></div>)}</div> : <p className="executive-empty">No station comparison data has been recorded yet. The view is connected to <code>/api/v1/dashboard/executive-summary</code>.</p>}</section></main>;
}
