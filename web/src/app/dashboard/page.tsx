import { AppShell } from "@/components/app-shell";
import { PageHeader, StatCard, StatusBadge } from "@/components/ui";
import { RiskTrend } from "@/components/risk-trend";
import { ApiNotice } from "@/components/api-notice";
import { EquipmentState } from "@/components/equipment-monitor";
import { EquipmentAttentionList } from "@/components/equipment-attention-list";
import { EquipmentAlerts } from "@/components/equipment-alerts";
import { WorkOrderQueue } from "@/components/work-order-queue";
import Link from "@/components/navigation-link";
import { requireSession, getRequestTimestamp } from "@/lib/session";
import {
  getMonitoring,
  getDashboardData,
  getEquipmentHistory,
} from "@/lib/api";
function value(number: number | undefined, suffix = "") {
  return number === undefined ? "—" : `${number}${suffix}`;
}
function age(timestamp?: string) {
  if (!timestamp) return "Not supplied";
  const minutes = Math.max(
    0,
    Math.round((Date.now() - Date.parse(timestamp)) / 60000),
  );
  return minutes < 1 ? "Just now" : `${minutes} min ago`;
}
function Empty({ children }: { children: string }) {
  return <div className="empty-state">{children}</div>;
}
export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{
    status?: string;
    equipment?: string;
    range?: string;
  }>;
}) {
  const session = await requireSession(["engineer"]);
  const supervisor = false;
  const { status = "", equipment: selected, range = "24" } = await searchParams;
  const [dashboard, monitoring] = await Promise.all([
    getDashboardData(session.token),
    getMonitoring(session.token),
  ]);
  const [
    summaryResponse,
    orderResponse,
    auditResponse,
    hseResponse,
    alertResponse,
  ] = dashboard;
  const summary = summaryResponse.data;
  const orders = orderResponse.data ?? [];
  const auditLogs = auditResponse.data ?? [];
  const hse = hseResponse.data;
  const alerts = alertResponse.data ?? [];
  const equipment = monitoring.data?.equipment ?? [];
  const asset =
    equipment.find((row) => row.equipment_id === selected)?.equipment_id ??
    equipment.find((row) => row.prediction)?.equipment_id ??
    equipment[0]?.equipment_id;
  const history = asset
    ? await getEquipmentHistory(asset, session.token)
    : null;
  const pending = orders.filter((order) =>
    ["PENDING_APPROVAL", "ESCALATED"].includes(order.status ?? ""),
  );
  return (
    <AppShell user={session.user}>
      <main className="engineer-workspace">
        <PageHeader
          title="Station Operations"
          description={`Welcome, ${session.user.name ?? session.user.id}. Review equipment signals and coordinate the next maintenance action.`}
        >
          <span className="secondary-link">
            {session.user.station_ids.join(", ") || "Network overview"}
          </span>
        </PageHeader>
        <ApiNotice result={summaryResponse} label="Summary unavailable" />
        <section className="stat-grid">
          <StatCard
            label="Needs Attention"
            value={monitoring.available ? equipment.filter(row => ["FAILURE_DETECTED", "APPROACHING_THRESHOLD"].includes(row.state)).length : "—"}
            detail="Evaluated assets requiring attention in your stations"
            icon="equipment"
            tone="red"
          />
          <StatCard
            label="Unscored Assets"
            value={monitoring.available ? equipment.filter(row => row.state === "UNSCORED").length : "?"}
            detail="Assets without a recorded model evaluation"
            icon="alerts"
            tone="red"
          />
          <StatCard
            label="Active Maintenance"
            value={orderResponse.available ? orders.filter(order => ["DISPATCHED", "IN_PROGRESS"].includes(order.status ?? "")).length : "?"}
            detail="Dispatched and in-progress work in your scope"
            icon="orders"
          />
          <StatCard
            label="Pending Review"
            value={orderResponse.available ? pending.length : "—"}
            detail="Pending approval and escalated in your scope"
            icon="clock"
            tone="amber"
          />
        </section>
        <p className="monitoring-context">
          These cards use equipment and work orders in your access scope. Simulator readings are labelled synthetic. Unscored
          equipment has not been established as healthy.
        </p>
        <div className="dashboard-layout">
          <div>
            <div className="dashboard-columns">
              <div>
                {history && !history.available && (
                  <ApiNotice
                    result={history}
                    label="Risk history unavailable"
                  />
                )}
                <RiskTrend
                  asOf={await getRequestTimestamp()}
                  readings={history?.data?.readings ?? []}
                  equipment={equipment}
                  selected={asset}
                  range={range}
                />
              </div>
              <section className="panel">
                <div className="panel-header">
                  <h3>Equipment Requiring Attention</h3>
                  <Link href="/equipment?state=FAILURE_DETECTED">
                    View equipment
                  </Link>
                </div>
                {!monitoring.available && (
                  <ApiNotice
                    result={monitoring}
                    label="Equipment monitoring unavailable"
                  />
                )}
                <EquipmentAttentionList
                  equipment={equipment}
                  available={monitoring.available}
                />
              </section>
            </div>
            <section className="panel" id="work-orders">
              <div className="panel-header">
                <h3>Recent Work Orders</h3>
                <Link href="/work-orders">View all</Link>
              </div>
              <ApiNotice
                result={orderResponse}
                label="Work order service unavailable"
              />
              <WorkOrderQueue
                orders={orders}
                status={status}
                supervisor={supervisor}
              />
            </section>
            <section className="dashboard-columns">
              <section className="panel">
                <div className="panel-header">
                  <h3>Fleet Evaluation</h3>
                </div>
                <div className="fleet-count">
                  <strong>
                    {monitoring.available ? equipment.length : "—"}
                  </strong>
                  <span>assets with recorded telemetry</span>
                </div>
                <div className="state-distribution" aria-hidden="true">
                  {[
                    "NORMAL",
                    "APPROACHING_THRESHOLD",
                    "FAILURE_DETECTED",
                    "UNSCORED",
                  ].map((state) => (
                    <span
                      key={state}
                      className={state.toLowerCase()}
                      style={{
                        width: `${equipment.length ? (equipment.filter((row) => row.state === state).length / equipment.length) * 100 : 0}%`,
                      }}
                    />
                  ))}
                </div>
                {[
                  "NORMAL",
                  "APPROACHING_THRESHOLD",
                  "FAILURE_DETECTED",
                  "UNSCORED",
                ].map((state) => (
                  <div className="fleet-row" key={state}>
                    <EquipmentState state={state} />
                    <b>
                      {monitoring.available
                        ? equipment.filter((row) => row.state === state).length
                        : "—"}
                    </b>
                  </div>
                ))}
              </section>
              <section className="panel">
                <div className="panel-header">
                  <h3>Backend Estimates</h3>
                </div>
                <div className="fleet-row">
                  <span>Simulated uptime</span>
                  <strong>{value(summary?.uptime_percentage, "%")}</strong>
                </div>
                <div className="fleet-row">
                  <span>Simulated downtime</span>
                  <strong>{value(summary?.downtime_minutes, "m")}</strong>
                </div>
                <p className="monitoring-context">
                  Estimated from work orders created in the past 24h. Recorded
                  equipment downtime is available in asset details.
                </p>
              </section>
            </section>
          </div>
          <aside className="dashboard-side">
            <section className="panel">
              <div className="panel-header">
                <h3>Recent Alerts</h3>
                <Link href="/alerts">View all</Link>
              </div>
              {!alertResponse.available && (
                <ApiNotice
                  result={alertResponse}
                  label="Failure alert service unavailable"
                />
              )}
              <div className="compact-list">
                {alerts.slice(0, 5).map((alert, index) => (
                  <Link
                    className="compact-item"
                    href={`/equipment/${encodeURIComponent(alert.equipment_id)}`}
                    key={alert.task_id ?? index}
                  >
                    <StatusBadge status={alert.severity} />
                    <strong>
                      {alert.failure_code?.replaceAll("_", " ") ??
                        "Maintenance alert"}
                    </strong>
                    <small>
                      {alert.equipment_id} · {age(alert.received_at)}
                    </small>
                  </Link>
                ))}
              </div>
              {alertResponse.available && !alerts.length && (
                <Empty>No failure alerts recorded.</Empty>
              )}
            </section>
            <section className="panel">
              <div className="panel-header">
                <h3>Pending Approvals</h3>
                <Link href="/approvals">View all</Link>
              </div>
              {pending.slice(0, 5).map((order) => (
                <Link
                  className="compact-item"
                  href={`/work-orders/${encodeURIComponent(order.work_order_id)}`}
                  key={order.work_order_id}
                >
                  <strong>{order.work_order_id}</strong>
                  <small>
                    {order.equipment_id} · {age(order.created_at)}
                  </small>
                  <StatusBadge status={order.status} />
                </Link>
              ))}
              {!pending.length && (
                <Empty>
                  {orderResponse.available
                    ? "No pending reviews."
                    : "Approval queue unavailable."}
                </Empty>
              )}
            </section>
          </aside>
        </div>
        <details className="panel">
          <summary>Alert evidence and maintenance handoff</summary>
          <div id="alerts">
            {alertResponse.available ? (
              <>
                <p className="monitoring-context">
                  Showing the five most recent alerts.{" "}
                  <Link href="/alerts">Open the full alert feed</Link>.
                </p>
                <EquipmentAlerts
                  alerts={alerts.slice(0, 5)}
                  orders={orders}
                  ordersAvailable={orderResponse.available}
                />
              </>
            ) : (
              <ApiNotice
                result={alertResponse}
                label="Failure alert service unavailable"
              />
            )}
          </div>
        </details>
        <details className="panel supporting-context"><summary>Station resources, safety and backend estimates</summary>
        {hse && (
          <section className="hse-band">
            <div className="hse-heading">
              <span className="eyebrow">
                HSE EARLY WARNING / SPILL PREVENTION
              </span>
              <h2>Loading safety monitor</h2>
              <p>
                Fill and flow analytics designed to stop overfill before an
                environmental incident.
              </p>
            </div>
            <div
              className={`hse-severity severity-${hse.severity.toLowerCase()}`}
            >
              <span className="severity-kicker">
                {hse.tank_id} / {hse.source}
              </span>
              <strong>{hse.severity}</strong>
              <span>{hse.recommended_action}</span>
            </div>
            <div className="hse-metrics">
              <div>
                <small>Tank level</small>
                <b>{hse.level_percent}%</b>
                <i>
                  <em style={{ width: `${hse.level_percent}%` }} />
                </i>
              </div>
              <div>
                <small>Flow rate</small>
                <b>{hse.flow_rate_lpm.toLocaleString()} L/min</b>
                <i>
                  <em
                    style={{
                      width: `${Math.min(100, (hse.flow_rate_lpm / hse.max_flow_rate_lpm) * 100)}%`,
                    }}
                  />
                </i>
              </div>
              <div>
                <small>Time to safe limit</small>
                <b>
                  {hse.minutes_to_safe_limit === null
                    ? "--"
                    : `${hse.minutes_to_safe_limit} min`}
                </b>
              </div>
            </div>
            <div className="hse-drivers">
              {hse.drivers.map((driver) => (
                <span key={driver}>+ {driver}</span>
              ))}
            </div>
          </section>
        )}
        <section className="dashboard-grid lower-grid">
          <article className="panel" id="audit">
            <div className="panel-header">
              <div>
                <span className="eyebrow">TRACEABILITY</span>
                <h3>Recent audit activity</h3>
              </div>
              <span className="integrity">
                <i />
                Backend status
              </span>
            </div>
            {auditLogs.length === 0 ? (
              <Empty>No audit entries returned by the API.</Empty>
            ) : (
              <div className="audit-list">
                {auditLogs.slice(0, 4).map((log) => (
                  <div className="audit-row" key={log.id}>
                    <span className="audit-marker" />
                    <div>
                      <strong>{log.event_name.replaceAll("_", " ")}</strong>
                      <span>{age(log.timestamp)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </article>
          <article className="panel snapshot-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">STATION SNAPSHOT</span>
                <h3>Simulated availability</h3>
              </div>
              <span className="snapshot-value">
                {value(summary?.uptime_percentage, "%")}
              </span>
            </div>
            <div className="readiness-bar">
              <span style={{ width: `${summary?.uptime_percentage ?? 0}%` }} />
            </div>
            <p>
              The backend estimates this percentage from simulated downtime; it
              is not measured equipment uptime.
            </p>
          </article>
        </section>
        <section className="dashboard-grid lower-grid">
          <article className="panel">
            <details>
              <summary>
                <strong>Simulated HR roster</strong>
              </summary>
              {summary?.available_technicians?.length ? (
                summary.available_technicians.map((tech) => (
                  <div className="health-row" key={tech.id}>
                    <strong>{tech.name}</strong>
                    <span>{tech.certs?.join(", ")}</span>
                  </div>
                ))
              ) : (
                <Empty>No technician availability returned.</Empty>
              )}
            </details>
          </article>
          <article className="panel">
            <details>
              <summary>
                <strong>Simulated parts inventory</strong>
              </summary>
              {summary?.inventory?.length ? (
                summary.inventory.map((part) => (
                  <div className="health-row" key={part.part_number}>
                    <strong>{part.part_number}</strong>
                    <span>
                      {part.quantity_available} available ?{" "}
                      {part.in_stock ? "In stock" : "Out of stock"}
                    </span>
                  </div>
                ))
              ) : (
                <Empty>No inventory returned.</Empty>
              )}
            </details>
          </article>
        </section>
        </details>
      </main>
    </AppShell>
  );
}
