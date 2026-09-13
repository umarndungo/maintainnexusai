import { MaintenanceControls } from "@/components/maintenance-controls";
import Link from "@/components/navigation-link";
import { requireSession } from "@/lib/session";
import { LiveUpdates } from "@/components/live-updates";
import { getLifecycle, getMaintenanceData } from "@/lib/api";
import { LogoutButton } from "@/components/logout-button";

export default async function WorkOrderPage({ params }: { params: Promise<{ id: string }> }) {
  const { token, user } = await requireSession(["engineer", "supervisor", "executive"]);
  const { id } = await params;
  const [result, maintenance] = await Promise.all([getLifecycle(id, token), getMaintenanceData(token)]);
  const order = maintenance[0].data?.find(order => order.work_order_id === id);
  const alert = maintenance[1].data?.find(alert => alert.task_id === order?.alert_task_id);
  const events = result.data ?? [];
  return <main className="detail-shell"><header className="detail-header"><div><span className="eyebrow">WORK ORDER / LIFE STORY</span><h1>{id}</h1><p>Every handoff, decision, and change in one accountable thread.</p></div><div className="detail-actions"><Link href="/dashboard">Back to station</Link><LiveUpdates /><LogoutButton /></div></header>{order && <section className="detail-panel monitoring-panel"><div className="panel-header"><Link href={`/equipment/${encodeURIComponent(order.equipment_id)}`}>{order.equipment_id}</Link><span className="equipment-state">{order.status?.replaceAll("_", " ")}</span></div><p>Assigned technician: {order.assigned_technician_id ?? "Not supplied"} ? Replacement part: {order.reserved_part ?? "Not supplied"}</p>{user.role !== "executive" && <MaintenanceControls key={`${order.status}-${order.assigned_technician_id}`} order={order} technicians={maintenance[2].data?.available_technicians ?? []} alert={alert} supervisor={user.role === "supervisor"} />}</section>}<section className="detail-panel">{!result.available && <p className="notice">Lifecycle service unavailable.</p>}{events.length ? <div className="timeline">{events.map((event) => <article className="timeline-item" key={event.id}><span className="timeline-dot" /><div><span className="eyebrow">{new Date(event.timestamp).toLocaleString()}</span><h2>{event.to_status.replaceAll("_", " ")}</h2><p>{event.note ?? "Lifecycle transition recorded."}</p><small>{event.actor_role} / {event.actor_id}</small>{event.risk_drivers?.slice(0, 3).map(driver => <p key={driver.feature}>{driver.reason}</p>)}{event.top_features?.slice(0, 3).map(feature => <p key={feature}>{feature}</p>)}</div></article>)}</div> : <div className="detail-empty">No lifecycle history was returned for this work order.</div>}</section></main>;
}
