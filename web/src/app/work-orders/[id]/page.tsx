import { workspacePath } from "@/lib/workspace";
import { ApiNotice } from "@/components/api-notice";
import { LifecycleEvidence } from "@/components/lifecycle-evidence";
import { EquipmentAlerts } from "@/components/equipment-alerts";
import { MaintenanceControls } from "@/components/maintenance-controls";
import Link from "@/components/navigation-link";
import { requireSession } from "@/lib/session";
import { AppShell } from "@/components/app-shell";
import { getLifecycle, getMaintenanceData } from "@/lib/api";


export default async function WorkOrderPage({ params }: { params: Promise<{ id: string }> }) {
  const { token, user } = await requireSession(["engineer", "supervisor", "executive"]);
  const { id } = await params;
  const [result, maintenance] = await Promise.all([getLifecycle(id, token), getMaintenanceData(token)]);
  const order = maintenance[0].data?.find(order => order.work_order_id === id);
  const alert = maintenance[1].data?.find(alert => alert.task_id === order?.alert_task_id);
  const events = result.data ?? [];
  return <AppShell user={user}><main className="detail-shell"><header className="detail-header"><div><span className="eyebrow">WORK ORDER / LIFE STORY</span><h1>{id}</h1><p>Every handoff, decision, and change in one accountable thread.</p></div><div className="detail-actions"><Link href={workspacePath(user.role)}>Back to workspace</Link></div></header><ApiNotice result={maintenance[0]} label="Work order details unavailable" />{order && <section className="detail-panel monitoring-panel"><div className="panel-header"><Link href={`/equipment/${encodeURIComponent(order.equipment_id)}`}>{order.equipment_id}</Link><span className="equipment-state">{order.status?.replaceAll("_", " ")}</span></div><p>Assigned technician: {order.assigned_technician_id ?? "Not supplied"} ? Replacement part: {order.reserved_part ?? "Not supplied"}</p>{user.role !== "executive" && <MaintenanceControls key={`${order.status}-${order.assigned_technician_id}`} order={order} technicians={maintenance[2].available ? maintenance[2].data?.available_technicians ?? [] : undefined} alert={alert} supervisor={user.role === "supervisor"} />}</section>}{alert && <EquipmentAlerts alerts={[alert]} orders={order ? [order] : []} ordersAvailable={maintenance[0].available} />}<ApiNotice result={maintenance[1]} label="Source alert unavailable" /><section className="detail-panel">{!result.available && <ApiNotice result={result} label="Lifecycle service unavailable" />}{events.length ? <div className="timeline">{events.map((event) => <article className="timeline-item" key={event.id}><span className="timeline-dot" /><div><span className="eyebrow">{new Date(event.timestamp).toLocaleString()}</span><h2>{event.to_status.replaceAll("_", " ")}</h2><p>{event.note ?? "Lifecycle transition recorded."}</p><small>{event.actor_role} / {event.actor_id}</small><LifecycleEvidence event={event} /></div></article>)}</div> : <div className="detail-empty">No lifecycle history was returned for this work order.</div>}</section></main></AppShell>;
}

