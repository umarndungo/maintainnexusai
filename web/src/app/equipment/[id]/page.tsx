import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getDowntime } from "@/lib/api";
import { LogoutButton } from "@/components/logout-button";

export default async function EquipmentPage({ params }: { params: Promise<{ id: string }> }) {
  const token = (await cookies()).get("maintainnexus_token")?.value;
  if (!token) redirect("/login");
  const { id } = await params;
  const result = await getDowntime(id, token);
  const windows = result.data ?? [];
  return <main className="detail-shell"><header className="detail-header"><div><span className="eyebrow">EQUIPMENT / RECOVERY STORY</span><h1>{id}</h1><p>Downtime windows and recovery history, kept close to the asset.</p></div><div className="detail-actions"><Link href="/dashboard">Back to station</Link><LogoutButton /></div></header><section className="detail-panel"><div className="panel-heading"><span className="eyebrow">DOWNTIME WINDOWS</span><h2>{windows.length ? `${windows.length} recorded window${windows.length === 1 ? "" : "s"}` : "No downtime windows yet"}</h2></div>{windows.length ? <div className="window-list">{windows.map((window) => <article key={window.id}><strong>{window.work_order_id ?? "Unlinked event"}</strong><span>{new Date(window.started_at).toLocaleString()} → {window.ended_at ? new Date(window.ended_at).toLocaleString() : "Still open"}</span><b>{window.estimated_cost === undefined ? "Cost pending" : `$${window.estimated_cost.toLocaleString()}`}</b></article>)}</div> : <p className="detail-empty">When a work order opens and closes a downtime window, its recovery will appear here.</p>}</section></main>;
}
