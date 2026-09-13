import { ApiNotice } from "@/components/api-notice";
import Link from "@/components/navigation-link";
import { EquipmentMonitor } from "@/components/equipment-monitor";
import { EquipmentAlerts } from "@/components/equipment-alerts";
import { LiveUpdates } from "@/components/live-updates";
import { LogoutButton } from "@/components/logout-button";
import { requireSession } from "@/lib/session";
import { getMonitoring, getMaintenanceData } from "@/lib/api";

export default async function MonitoringPage({ searchParams }: { searchParams: Promise<{ state?: string }> }) {
  const { token, user } = await requireSession(["engineer", "supervisor", "executive"]);
  const workspace = user.role === "executive" ? "/executive" : "/dashboard";
  const { state = "" } = await searchParams;
  const [monitoring, maintenance] = await Promise.all([getMonitoring(token), getMaintenanceData(token)]);
  const [orders, alerts] = maintenance;
  const equipment = (monitoring.data?.equipment ?? []).filter(reading => !state || reading.state === state);
  return <main className="detail-shell equipment-workspace"><header className="detail-header"><div><span className="eyebrow">OPERATIONS / EQUIPMENT WATCH</span><h1>Equipment monitoring</h1><p>Incoming readings, server-evaluated risk, and maintenance handoffs.</p></div><div className="detail-actions"><Link href={workspace}>Back to workspace</Link><LiveUpdates /><LogoutButton /></div></header><nav className="monitoring-filters" aria-label="Equipment state filters">{[["", "All equipment"], ["NORMAL", "Normal"], ["APPROACHING_THRESHOLD", "Approaching threshold"], ["FAILURE_DETECTED", "Requires attention"], ["UNSCORED", "Unscored"]].map(([value, label]) => value === "APPROACHING_THRESHOLD" && monitoring.data?.thresholds.warning_probability === null ? <span className="unavailable-filter" key={value}>Approaching threshold (not configured)</span> : <Link key={value} className={state === value ? "selected" : ""} href={value ? `/equipment?state=${value}` : "/equipment"}>{label}</Link>)}</nav>{monitoring.data ? <EquipmentMonitor equipment={equipment} thresholds={monitoring.data.thresholds} filtered={Boolean(state)} /> : <section className="panel monitoring-panel"><ApiNotice result={monitoring} label="Equipment monitoring unavailable" /><Link href="/equipment">Retry monitoring</Link></section>}{!orders.available && <ApiNotice result={orders} label="Maintenance service unavailable; assignment status cannot be confirmed" />}{alerts.available ? <EquipmentAlerts alerts={alerts.data ?? []} orders={orders.data ?? []} ordersAvailable={orders.available} /> : <ApiNotice result={alerts} label="Failure alert service unavailable" />}</main>;
}
