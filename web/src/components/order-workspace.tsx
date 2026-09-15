import { AppShell } from "./app-shell";
import { PageHeader, StatCard } from "./ui";
import { WorkOrderQueue } from "./work-order-queue";
import { ApiNotice } from "./api-notice";
import { requireSession } from "@/lib/session";
import { getMaintenanceData } from "@/lib/api";
export async function OrderWorkspace({
  approvals = false,
  status = "",
}: {
  approvals?: boolean;
  status?: string;
}) {
  const { token, user } = await requireSession(["engineer", "supervisor"]);
  const [result] = await getMaintenanceData(token);
  const all = result.data ?? [];
  const orders = approvals
    ? all.filter((order) =>
        ["PENDING_APPROVAL", "ESCALATED"].includes(order.status ?? ""),
      )
    : all;
  return (
    <AppShell user={user}>
      <main>
        <PageHeader
          title={approvals ? "Approvals" : "Work Orders"}
          description={
            approvals
              ? "Review pending maintenance requests and escalated work orders."
              : "Track and manage maintenance work orders across your accessible assets."
          }
        />
        <section className="stat-grid">
          <StatCard
            label={approvals ? "Awaiting Review" : "Total Work Orders"}
            value={result.available ? orders.length : "—"}
            detail="In your accessible scope"
            icon="orders"
          />
          {(approvals
            ? ["PENDING_APPROVAL", "ESCALATED"]
            : ["PENDING_APPROVAL", "IN_PROGRESS", "COMPLETED"]
          ).map((state) => (
            <StatCard
              key={state}
              label={state.replaceAll("_", " ").toLowerCase()}
              value={
                result.available
                  ? orders.filter((order) => order.status === state).length
                  : "—"
              }
              detail="Canonical backend lifecycle status"
              icon={state === "COMPLETED" ? "approvals" : "clock"}
              tone={state === "COMPLETED" ? "green" : "amber"}
            />
          ))}
        </section>
        <section className="panel">
          <div className="panel-header">
            <h3>{approvals ? "Approval Queue" : "Work Order Register"}</h3>
            <span>Role: {user.role}</span>
          </div>
          <ApiNotice result={result} label="Work order service unavailable" />
          <WorkOrderQueue
            orders={orders}
            status={status}
            supervisor={user.role === "supervisor"}
          />
        </section>
      </main>
    </AppShell>
  );
}
