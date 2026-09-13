import Link from "next/link";
import { requireSession } from "@/lib/session";
import { LiveUpdates } from "@/components/live-updates";
import { getLifecycle } from "@/lib/api";
import { LogoutButton } from "@/components/logout-button";

export default async function WorkOrderPage({ params }: { params: Promise<{ id: string }> }) {
  const { token } = await requireSession(["engineer", "supervisor", "executive"]);
  const { id } = await params;
  const result = await getLifecycle(id, token);
  const events = result.data ?? [];
  return <main className="detail-shell"><header className="detail-header"><div><span className="eyebrow">WORK ORDER / LIFE STORY</span><h1>{id}</h1><p>Every handoff, decision, and change in one accountable thread.</p></div><div className="detail-actions"><Link href="/dashboard">Back to station</Link><LiveUpdates /><LogoutButton /></div></header><section className="detail-panel">{!result.available && <p className="notice">Lifecycle service unavailable.</p>}{events.length ? <div className="timeline">{events.map((event) => <article className="timeline-item" key={event.id}><span className="timeline-dot" /><div><span className="eyebrow">{new Date(event.timestamp).toLocaleString()}</span><h2>{event.to_status.replaceAll("_", " ")}</h2><p>{event.note ?? "Lifecycle transition recorded."}</p><small>{event.actor_role} / {event.actor_id}</small>{event.risk_drivers?.slice(0, 3).map(driver => <p key={driver.feature}>{driver.reason}</p>)}{event.top_features?.slice(0, 3).map(feature => <p key={feature}>{feature}</p>)}</div></article>)}</div> : <div className="detail-empty">No lifecycle history was returned for this work order.</div>}</section></main>;
}
