import Link from "@/components/navigation-link";
import { EquipmentMonitor } from "@/components/equipment-monitor";
import { EquipmentAlerts } from "@/components/equipment-alerts";
import { LiveUpdates } from "@/components/live-updates";
import { LogoutButton } from "@/components/logout-button";
import { requireSession } from "@/lib/session";
import { getMonitoring, getMaintenanceData } from "@/lib/api";

export default async function MonitoringPage({ searchParams }: { searchParams: Promise<{ state?: string }> }) {
  const { token } = await requireSession(["engineer", "supervisor"]);
  const { state = "" } = await searchParams;
  const [monitoring, maintenance] = await Promise.all([getMonitoring(token), getMaintenanceData(token)]);
  const [orders, alerts] = maintenance;
  const equipment = (monitoring.data?.equipment ?? []).filter(reading => !state || reading.state === state);
  return <main className="detail-shell equipment-workspace"><header className="detail-header"><div><span className="eyebrow">OPERATIONS / EQUIPMENT WATCH</span><h1>Equipment monitoring</h1><p>Incoming readings, server-evaluated risk, and maintenance handoffs.</p></div><div className="detail-actions"><Link href="/dashboard">Station overview</Link><LiveUpdates /><LogoutButton /></div></header><nav className="monitoring-filters" aria-label="Equipment state filters">{[["", "All equipment"], ["NORMAL", "Normal"], ["APPROACHING_THRESHOLD", "Approaching threshold"], ["FAILURE_DETECTED", "Requires attention"], ["UNSCORED", "Awaiting evaluation"]].map(([value, label]) => <Link key={value} className={state === value ? "selected" : ""} href={value ? `/equipment?state=${value}` : "/equipment"}>{label}</Link>)}</nav>{monitoring.data ? <EquipmentMonitor equipment={equipment} thresholds={monitoring.data.thresholds} /> : <section className="panel monitoring-panel"><p className="notice">Equipment monitoring is unavailable. Check that the API is running the current version.</p><Link href="/equipment">Retry monitoring</Link></section>}{!orders.available && <p className="notice">Maintenance service unavailable. Assignment status cannot be confirmed.</p>}{alerts.available ? <EquipmentAlerts alerts={alerts.data ?? []} orders={orders.data ?? []} /> : <p className="notice">Failure alert service unavailable.</p>}</main>;
}
