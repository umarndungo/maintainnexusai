import { AppShell } from "@/components/app-shell";
import { PageHeader, StatCard } from "@/components/ui";
import { EquipmentMonitor } from "@/components/equipment-monitor";
import { RiskTrend } from "@/components/risk-trend";
import { ApiNotice } from "@/components/api-notice";
import { getMonitoring, getEquipmentHistory } from "@/lib/api";
import { requireSession, getRequestTimestamp } from "@/lib/session";
export default async function MonitoringPage({
  searchParams,
}: {
  searchParams: Promise<{ equipment?: string; range?: string }>;
}) {
  const { token, user } = await requireSession([
    "engineer",
    "supervisor",
    "executive",
  ]);
  const { equipment: selected, range = "1" } = await searchParams;
  const result = await getMonitoring(token);
  const equipment = result.data?.equipment ?? [];
  const asset =
    equipment.find((row) => row.equipment_id === selected)?.equipment_id ??
    equipment.find((row) => row.prediction)?.equipment_id ??
    equipment[0]?.equipment_id;
  const history = asset ? await getEquipmentHistory(asset, token) : null;
  return (
    <AppShell user={user}>
      <main>
        <PageHeader
          title="Live Monitoring"
          description="Persisted sensor readings, server-evaluated failure risk and asset state."
        />
        <section className="stat-grid">
          <StatCard
            label="Equipment Monitored"
            value={result.available ? equipment.length : "—"}
            detail="Assets with recorded readings"
            icon="equipment"
          />
          {[
            ["NORMAL", "Normal"],
            ["FAILURE_DETECTED", "Failure risk detected"],
            ["UNSCORED", "Unscored"],
          ].map(([state, label]) => (
            <StatCard
              key={state}
              label={label}
              value={
                result.available
                  ? equipment.filter((row) => row.state === state).length
                  : "—"
              }
              detail="Latest recorded evaluation"
              icon={state === "NORMAL" ? "approvals" : "alerts"}
              tone={
                state === "NORMAL"
                  ? "green"
                  : state === "UNSCORED"
                    ? "neutral"
                    : "red"
              }
            />
          ))}
        </section>
        <ApiNotice result={result} label="Equipment monitoring unavailable" />
        <div className="monitoring-layout">
          <div>
            {result.data && (
              <EquipmentMonitor
                equipment={equipment}
                thresholds={result.data.thresholds}
              />
            )}
          </div>
          <div>
            {history && (
              <ApiNotice result={history} label="Sensor history unavailable" />
            )}
            <RiskTrend
              asOf={await getRequestTimestamp()}
              equipment={equipment}
              readings={history?.data?.readings ?? []}
              selected={asset}
              range={range}
              basePath="/monitoring"
            />
            <section className="panel">
              <div className="panel-header">
                <h3>Live Data Source</h3>
              </div>
              <p className="monitoring-context">
                {result.data?.source ?? "Backend unavailable"}. The existing
                authenticated event stream updates this view. Synthetic
                simulation measurements remain labelled as synthetic.
              </p>
            </section>
          </div>
        </div>
      </main>
    </AppShell>
  );
}
