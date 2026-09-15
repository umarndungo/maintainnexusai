import { AppShell } from "@/components/app-shell";
import { PageHeader, StatCard } from "@/components/ui";
import { AlertsTable } from "@/components/alerts-table";
import { ApiNotice } from "@/components/api-notice";
import { requireSession } from "@/lib/session";
import { getMaintenanceData } from "@/lib/api";
export default async function AlertsPage() {
  const { token, user } = await requireSession([
    "engineer",
    "supervisor",
    "executive",
  ]);
  const [orders, result, roster] = await getMaintenanceData(token);
  const alerts = result.data ?? [];
  return (
    <AppShell user={user}>
      <main>
        <PageHeader
          title="Alerts"
          description="Monitor, investigate and act on recorded maintenance alerts."
        />
        <section className="stat-grid">
          <StatCard
            label="Recorded Alerts"
            value={result.available ? alerts.length : "—"}
            detail="Alerts returned in your access scope"
            icon="alerts"
            tone="red"
          />
          {["CRITICAL", "HIGH", "MEDIUM"].map((severity) => (
            <StatCard
              key={severity}
              label={severity.toLowerCase()}
              value={
                result.available
                  ? alerts.filter((alert) => alert.severity === severity).length
                  : "—"
              }
              detail="Recorded severity from backend"
              icon="alerts"
              tone={severity === "MEDIUM" ? "amber" : "red"}
            />
          ))}
        </section>
        <ApiNotice result={result} label="Failure alert service unavailable" />
        <ApiNotice result={orders} label="Maintenance service unavailable" />
        <AlertsTable
          alerts={alerts}
          orders={orders.data ?? []}
          technicians={roster.data?.available_technicians}
          allowAssignment={
            user.role !== "executive" && orders.available && roster.available
          }
          ordersAvailable={orders.available}
        />
      </main>
    </AppShell>
  );
}
