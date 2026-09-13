import Link from "next/link";
import { requireSession } from "@/lib/session";
import { LiveUpdates } from "@/components/live-updates";
import { getDowntime, getDashboardData } from "@/lib/api";
import { LogoutButton } from "@/components/logout-button";

export default async function EquipmentPage({ params }: { params: Promise<{ id: string }> }) {
  const { token } = await requireSession(["engineer", "supervisor"]);
  const { id } = await params;
  const [result, dashboard] = await Promise.all([getDowntime(id, token), getDashboardData(token)]);
  const orders = (dashboard[1].data ?? []).filter(order => order.equipment_id === id);
  const windows = result.data ?? [];
  return <main className="detail-shell"><header className="detail-header"><div><span className="eyebrow">EQUIPMENT / RECOVERY STORY</span><h1>{id}</h1><p>Downtime windows and recovery history, kept close to the asset.</p></div><div className="detail-actions"><Link href="/dashboard">Back to station</Link><LiveUpdates /><LogoutButton /></div></header><section className="detail-panel">{!result.available && <p className="notice">Downtime service unavailable.</p>}<div className="panel-heading"><span className="eyebrow">DOWNTIME WINDOWS</span><h2>{windows.length ? `${windows.length} recorded window${windows.length === 1 ? "" : "s"}` : "No downtime windows yet"}</h2></div>{windows.length ? <div className="window-list">{windows.map((window) => <article key={window.id}><strong>{window.work_order_id ? <Link href={`/work-orders/${encodeURIComponent(window.work_order_id)}`}>{window.work_order_id}</Link> : "Unlinked event"}</strong><span>{new Date(window.started_at).toLocaleString()} → {window.ended_at ? new Date(window.ended_at).toLocaleString() : "Still open"}</span><b>{window.estimated_cost === undefined ? "Cost pending" : `$${window.estimated_cost.toLocaleString()}`}</b></article>)}</div> : <p className="detail-empty">When a work order opens and closes a downtime window, its recovery will appear here.</p>}</section><section className="detail-panel"><h2>Maintenance history</h2>{!dashboard[1].available ? <p className="notice">Maintenance history unavailable.</p> : orders.length ? orders.map(order => <div className="health-row" key={order.work_order_id}><Link href={`/work-orders/${encodeURIComponent(order.work_order_id)}`}>{order.work_order_id}</Link><span>{order.status?.replaceAll("_", " ")}</span></div>) : <p>No work orders returned for this equipment.</p>}</section></main>;
}
