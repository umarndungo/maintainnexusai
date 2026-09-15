import { Suspense } from "react";
import type { CurrentUser } from "@/lib/api";
import { EquipmentRetry } from "@/components/equipment-retry";
import "./equipment.css";
import { workspacePath } from "@/lib/workspace";
import { ApiNotice } from "@/components/api-notice";
import Link from "@/components/navigation-link";
import { EquipmentMonitor } from "@/components/equipment-monitor";
import { EquipmentAlerts } from "@/components/equipment-alerts";
import { AppShell } from "@/components/app-shell";

import { requireSession } from "@/lib/session";
import { getMonitoring, getMaintenanceData } from "@/lib/api";

export default async function EquipmentPage({ searchParams }: { searchParams: Promise<{ state?: string }> }) {
  const { token, user } = await requireSession(["engineer", "supervisor", "executive"]);
  return <AppShell user={user}><Suspense fallback={<main className="equipment-workspace"><h1>Equipment</h1><div className="panel equipment-table-skeleton" role="status" aria-label="Loading equipment activity">Loading equipment activity{Array.from({length:6}, (_, index) => <span key={index} />)}</div></main>}><EquipmentContent token={token} user={user} searchParams={searchParams} /></Suspense></AppShell>;
}

async function EquipmentContent({ token, user, searchParams }: { token: string; user: CurrentUser; searchParams: Promise<{ state?: string }> }) {
  const workspace = workspacePath(user.role);
  const { state = "" } = await searchParams;
  const [monitoring, maintenance] = await Promise.all([getMonitoring(token), getMaintenanceData(token)]);
  const [orders, alerts] = maintenance;
  const equipment = (monitoring.data?.equipment ?? []).filter(reading => !state || reading.state === state);
  return <main className="detail-shell equipment-workspace"><header className="detail-header"><div><span className="eyebrow">OPERATIONS / EQUIPMENT WATCH</span><h1>Equipment</h1><p>Monitor equipment and related maintenance activity across your operational scope.</p></div><div className="detail-actions"><Link href={workspace}>Back to workspace</Link></div></header><nav className="monitoring-filters" aria-label="Equipment state filters">{[["", "All equipment"], ["NORMAL", "Normal"], ["APPROACHING_THRESHOLD", "Approaching threshold"], ["FAILURE_DETECTED", "Requires attention"], ["UNSCORED", "Unscored"]].map(([value, label]) => value === "APPROACHING_THRESHOLD" && monitoring.data?.thresholds.warning_probability === null ? <span className="unavailable-filter" key={value}>Approaching threshold (not configured)</span> : <Link key={value} className={state === value ? "selected" : ""} href={value ? `/equipment?state=${value}` : "/equipment"}>{label}</Link>)}</nav>{monitoring.data ? <EquipmentMonitor equipment={equipment} thresholds={monitoring.data.thresholds} filtered={Boolean(state)} /> : <section className="panel monitoring-panel"><ApiNotice result={monitoring} label="Equipment monitoring unavailable" /><Link href="/equipment">Retry monitoring</Link></section>}{!orders.available && <ApiNotice result={orders} label="Maintenance service unavailable; assignment status cannot be confirmed" />}{alerts.available ? <EquipmentAlerts alerts={alerts.data ?? []} orders={orders.data ?? []} ordersAvailable={orders.available} /> : <section className="panel"><h2>Unable to load equipment activity</h2><p>We couldn&apos;t retrieve the latest records.</p><EquipmentRetry /></section>}</main>;
}

