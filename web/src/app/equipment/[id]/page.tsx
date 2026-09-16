import { workspacePath } from "@/lib/workspace";
import { ApiNotice } from "@/components/api-notice";
import { PredictionDetails } from "@/components/prediction-details";
import Link from "@/components/navigation-link";
import { requireSession } from "@/lib/session";
import { AppShell } from "@/components/app-shell";
import { EquipmentState } from "@/components/equipment-monitor";
import { EquipmentTrends } from "@/components/equipment-trends";
import { EquipmentAlerts } from "@/components/equipment-alerts";
import { MaintenanceControls } from "@/components/maintenance-controls";
import { DowntimeHistoryList } from "@/components/downtime-history-list";
import { getDowntime, getEquipmentHistory, getMaintenanceData } from "@/lib/api";


export default async function EquipmentPage({ params }: { params: Promise<{ id: string }> }) {
  const session = await requireSession(["engineer", "supervisor", "executive"]);
  const { id } = await params;
  const readOnly = session.user.role === "executive";
  const workspace = workspacePath(session.user.role);
  const [history, downtime, maintenance] = await Promise.all([getEquipmentHistory(id, session.token), getDowntime(id, session.token), getMaintenanceData(session.token)]);
  const [orderResult, alertResult, roster] = maintenance;
  const orders = (orderResult.data ?? []).filter(order => order.equipment_id === id);
  const alerts = (alertResult.data ?? []).filter(alert => alert.equipment_id === id);
  const technicians = roster.data?.available_technicians ?? [];
  const readings = history.data?.readings ?? [];
  const latest = readings[readings.length - 1];
  const windows = downtime.data ?? [];
  return <AppShell user={session.user}><main className="detail-shell equipment-workspace"><header className="detail-header"><div><span className="eyebrow">EQUIPMENT / MONITORING & RECOVERY</span><h1>{id}</h1><p>{latest?.station_id ?? "Equipment station not supplied"} ? Sensor data, failure events, and accountable maintenance.</p></div><div className="detail-actions"><Link href="/equipment">All equipment</Link><Link href={workspace}>Back to workspace</Link></div></header>
    <section className="panel monitoring-panel"><div className="panel-header"><h3>Current equipment evaluation</h3>{latest && <EquipmentState state={latest.state} />}</div>{!history.available ? <><ApiNotice result={history} label="Equipment history unavailable" /><Link href={`/equipment/${encodeURIComponent(id)}`}>Retry</Link></> : latest ? <><div className="equipment-readings"><span>Failure probability<strong>{latest.prediction ? `${(latest.prediction.failure_probability * 100).toFixed(1)}%` : "Unscored"}</strong></span><span>Failure threshold<strong>{latest.prediction ? `${(latest.prediction.threshold * 100).toFixed(1)}%` : "Evaluation unavailable"}</strong></span><span>Last sensor reading<strong>{new Date(String(latest.telemetry.timestamp ?? latest.received_at)).toLocaleString()}</strong></span></div>{latest.evaluation_reason && <p className="notice">{latest.evaluation_reason}</p>}<p className="monitoring-context">Recorded by the backend: {new Date(latest.received_at).toLocaleString()}. Asset type: {latest.telemetry.asset_type ?? "Not supplied"}. Operating state: {latest.telemetry.operating_state ?? "Not supplied"}. Alarm code: {latest.telemetry.alarm_code ?? "Not supplied"}.</p>{latest.prediction && <PredictionDetails prediction={latest.prediction} />}</> : <p className="empty-state">No accessible sensor history for this equipment. Health has not been established.</p>}</section>
    {history.available && <EquipmentTrends readings={readings} />}
    {alertResult.available ? <EquipmentAlerts hideEquipment alerts={alerts} orders={orders} technicians={roster.available ? technicians : undefined} allowAssignment={!readOnly && orderResult.available && roster.available} ordersAvailable={orderResult.available} /> : <ApiNotice result={alertResult} label="Failure alerts unavailable" />}
    <section className="panel monitoring-panel"><div className="panel-header"><div><span className="eyebrow">MAINTENANCE WORKFLOW</span><h3>Assignments & repair progress</h3></div></div><p className="monitoring-context">{roster.data?.source}</p><p className="monitoring-context">Failure alert ? assigned task awaiting approval ? dispatched ? in progress ? completed. Completing a task does not overwrite equipment readings.</p>{!roster.available && <ApiNotice result={roster} label="Technician roster unavailable" />}{!orderResult.available ? <ApiNotice result={orderResult} label="Maintenance history unavailable" /> : orders.length ? <div className="maintenance-list">{orders.map(order => <article className="maintenance-card" key={order.work_order_id}><div className="panel-header"><Link href={`/work-orders/${encodeURIComponent(order.work_order_id)}`}><strong>{order.work_order_id}</strong></Link><span className="equipment-state">{order.status?.replaceAll("_", " ") ?? "Status unavailable"}</span></div><p>Assigned to {technicians.find(tech => tech.id === order.assigned_technician_id)?.name ?? order.assigned_technician_id ?? "Not supplied"} ? Part: {order.reserved_part ?? "Not supplied"}</p>{!readOnly && <MaintenanceControls key={`${order.status}-${order.assigned_technician_id}`} order={order} technicians={roster.available ? technicians : undefined} alert={alerts.find(alert => alert.task_id === order.alert_task_id)} supervisor={session.user.role === "supervisor"} />}</article>)}</div> : <p className="empty-state">No maintenance tasks returned for this equipment.</p>}</section>
    <section className="panel monitoring-panel"><div className="panel-header"><h3>Downtime & recovery history</h3></div>{!downtime.available ? <ApiNotice result={downtime} label="Downtime history unavailable" /> : windows.length ? <DowntimeHistoryList windows={windows} /> : <p className="empty-state">No recorded downtime windows. A window opens on dispatch and closes on maintenance completion.</p>}</section>
  </main></AppShell>;
}

