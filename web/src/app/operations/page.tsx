import { AppShell } from "@/components/app-shell";
import { ApiNotice } from "@/components/api-notice";
import { StatCard, StatusBadge } from "@/components/ui";
import Link from "@/components/navigation-link";
import { workspacePath } from "@/lib/workspace";
import { requireSession } from "@/lib/session";
import { getOperationsData } from "@/lib/api";

function Empty({ children }: { children: string }) {
  return <div className="empty-state">{children}</div>;
}

export default async function OperationsPage() {
  const { token, user } = await requireSession(["engineer", "supervisor", "executive"]);
  const [decisionsResult, loadingPointsResult] = await getOperationsData(token);
  const decisions = decisionsResult.data?.decisions ?? [];
  const loadingPoints = loadingPointsResult.data?.loading_points ?? [];
  const unavailable = loadingPoints.filter((bay) => bay.capacity_status !== "AVAILABLE");
  return (
    <AppShell user={user}>
      <main className="detail-shell">
        <header className="detail-header">
          <div>
            <span className="eyebrow">PREDICT / DECIDE / ACT</span>
            <h1>Decision Engine</h1>
            <p>
              Automated loading-bay rerouting decisions, kept fully separate
              from the alert → work-order repair path.
            </p>
          </div>
          <div className="detail-actions">
            <Link href={workspacePath(user.role)}>Back to workspace</Link>
          </div>
        </header>
        <section className="stat-grid">
          <StatCard
            label="Loading Bays"
            value={loadingPointsResult.available ? loadingPoints.length : "—"}
            detail="Bays known to the decision engine"
            icon="equipment"
          />
          <StatCard
            label="Unavailable Bays"
            value={loadingPointsResult.available ? unavailable.length : "—"}
            detail="Currently pulled from service"
            icon="alerts"
            tone={unavailable.length ? "red" : "neutral"}
          />
          <StatCard
            label="Reroute Decisions"
            value={decisionsResult.available ? decisions.length : "—"}
            detail="Most recent, newest first"
            icon="orders"
          />
        </section>
        <section className="detail-panel">
          <h2>Loading bays</h2>
          <p className="monitoring-context">
            A bay is marked unavailable automatically when its equipment&apos;s
            risk crosses the policy threshold; the next scheduled truck is
            rerouted to an alternate bay in the same call.
          </p>
          {!loadingPointsResult.available && (
            <ApiNotice
              result={loadingPointsResult}
              label="Loading-point service unavailable"
            />
          )}
          {loadingPointsResult.available && !loadingPoints.length && (
            <Empty>No loading bays have been recorded yet.</Empty>
          )}
          {loadingPoints.length > 0 && (
            <div className="equipment-grid">
              {loadingPoints.map((bay) => (
                <article className="maintenance-card" key={bay.id}>
                  <div className="panel-header">
                    <strong>{bay.bay_code}</strong>
                    <StatusBadge status={bay.capacity_status} />
                  </div>
                  <p>
                    Equipment: {bay.equipment_id ?? "Not supplied"}
                    <br />
                    Station: {bay.station_id ?? "Not supplied"}
                    <br />
                    Product: {bay.supported_product ?? "Not supplied"}
                  </p>
                </article>
              ))}
            </div>
          )}
        </section>
        <section className="detail-panel">
          <h2>Recent reroute decisions</h2>
          {!decisionsResult.available && (
            <ApiNotice
              result={decisionsResult}
              label="Decision service unavailable"
            />
          )}
          {decisionsResult.available && !decisions.length && (
            <Empty>No reroute decisions have been recorded yet.</Empty>
          )}
          {decisions.length > 0 && (
            <div className="audit-list">
              {decisions.map((decision) => (
                <article className="audit-row" key={decision.id}>
                  <span className="audit-marker" />
                  <div>
                    <strong>
                      {decision.decision_type.replaceAll("_", " ")}
                      {" · "}
                      {decision.affected_equipment_id ?? "Equipment not supplied"}
                    </strong>
                    <span>{new Date(decision.created_at).toLocaleString()}</span>
                    <p>{decision.reason}</p>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
    </AppShell>
  );
}
