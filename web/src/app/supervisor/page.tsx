import Link from "@/components/navigation-link";
import { AppShell } from "@/components/app-shell";
import { ApiNotice } from "@/components/api-notice";
import { PageHeader, StatCard } from "@/components/ui";
import { WorkOrderQueue } from "@/components/work-order-queue";
import { getMaintenanceData, getMonitoring, getExecutiveSummary } from "@/lib/api";
import { requireSession } from "@/lib/session";

export default async function SupervisorPage({ searchParams }: { searchParams: Promise<{ status?: string }> }) {
  const { user, token } = await requireSession(["supervisor"]);
  const { status = "" } = await searchParams;
  const [[ordersResult, , rosterResult], monitoring, outcomes] = await Promise.all([
    getMaintenanceData(token), getMonitoring(token), getExecutiveSummary(token),
  ]);
  const orders = ordersResult.data ?? [];
  const escalated = orders.filter(order => order.status === "ESCALATED");
  const pending = orders.filter(order => order.status === "PENDING_APPROVAL");
  const roster = rosterResult.data?.available_technicians ?? [];
  const counts = new Map<string, number>();
  for (const order of orders) counts.set(order.status ?? "UNKNOWN", (counts.get(order.status ?? "UNKNOWN") ?? 0) + 1);
  const attention = (monitoring.data?.equipment ?? []).filter(row => ["FAILURE_DETECTED", "APPROACHING_THRESHOLD"].includes(row.state));
  return <AppShell user={user}><main className="supervisor-workspace">
    <div className="role-intro"><span className="eyebrow">SUPERVISOR / NETWORK COORDINATION</span><PageHeader title="Maintenance Coordination" description="Resolve escalations, review requests and coordinate available maintenance resources."><Link className="secondary-link" href="/reports">View network outcomes</Link></PageHeader></div>
    <section className="stat-grid">
      <StatCard label="Escalated Orders" value={ordersResult.available ? escalated.length : "—"} detail="Recorded escalations requiring review" icon="alerts" tone="red" />
      <StatCard label="Awaiting Approval" value={ordersResult.available ? pending.length : "—"} detail="Pending approval in your accessible scope" icon="approvals" tone="amber" />
      <StatCard label="In Progress" value={ordersResult.available ? orders.filter(order => order.status === "IN_PROGRESS").length : "—"} detail="Maintenance with an in-progress lifecycle status" icon="orders" />
      <StatCard label="Available Technicians" value={rosterResult.available ? roster.length : "—"} detail="Available roster returned by the backend" icon="user" />
    </section>
    <div className="coordination-layout"><div>
      <section className="panel decision-panel"><div className="panel-header"><div><span className="eyebrow">PRIORITY REVIEW</span><h2>Escalation desk</h2></div><span className="role-count">{ordersResult.available ? escalated.length : "—"}</span></div><ApiNotice result={ordersResult} label="Escalation queue unavailable" />{ordersResult.available && <WorkOrderQueue orders={escalated} status="" supervisor />}</section>
      <section className="panel"><div className="panel-header"><h2>Approval desk</h2><Link href="/approvals">All reviews</Link></div><ApiNotice result={ordersResult} label="Approval queue unavailable" />{ordersResult.available && <WorkOrderQueue orders={pending} status={status} supervisor />}</section>
    </div><aside className="coordination-side">
      <section className="panel"><div className="panel-header"><h3>Workload by status</h3><Link href="/work-orders">Register</Link></div><ApiNotice result={ordersResult} label="Workload unavailable" />{ordersResult.available && (orders.length ? [...counts].map(([state, count]) => <div className="workload-row" key={state}><div><span>{state.replaceAll("_", " ")}</span><strong>{count}</strong></div><meter min={0} max={orders.length} value={count} aria-label={`${state}: ${count} of ${orders.length} work orders`} /></div>) : <p className="empty-state">No recorded work orders.</p>)}</section>
      <section className="panel"><div className="panel-header"><h3>Available team</h3></div><ApiNotice result={rosterResult} label="Technician roster unavailable" /><p className="monitoring-context">{rosterResult.data?.source}</p>{rosterResult.available && (roster.length ? roster.map(tech => <article className="team-row" key={tech.id}><strong>{tech.name}</strong><span>{tech.certs.join(", ") || "Certifications not supplied"}</span><small>{tech.active_work_orders} active work orders · {tech.on_shift ? "On shift" : "Off shift"}</small></article>) : <p className="empty-state">No available technicians returned.</p>)}</section>
      <section className="panel"><div className="panel-header"><h3>Equipment needing intervention</h3></div><ApiNotice result={monitoring} label="Equipment unavailable" />{monitoring.available && (attention.length ? attention.slice(0, 8).map(row => <Link className="compact-item" key={row.id} href={`/equipment/${encodeURIComponent(row.equipment_id)}`}><strong>{row.equipment_id}</strong><small>{row.station_id ?? "Station not supplied"} · {row.state.replaceAll("_", " ")}</small></Link>) : <p className="empty-state">No evaluated assets currently require intervention.</p>)}{attention.length > 8 && <Link href="/equipment">View all equipment</Link>}</section>
      <section className="panel"><h3>Recorded network downtime</h3><ApiNotice result={outcomes} label="Downtime unavailable" /><strong className="outcome-value">{outcomes.data?.downtime_minutes ?? "—"}<small> min</small></strong><p className="monitoring-context">Accumulated downtime windows, including those still open.</p></section>
    </aside></div>
  </main></AppShell>;
}
