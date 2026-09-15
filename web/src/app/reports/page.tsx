import { AppShell } from "@/components/app-shell";
import { ReportsWorkspace } from "@/components/reports-workspace";
import { requireSession, getRequestTimestamp } from "@/lib/session";
import { getReportSources, getDowntime } from "@/lib/api";
import type { ReportWindow } from "@/lib/report-data";

export default async function ReportsPage() {
  const { user, token } = await requireSession(["supervisor", "executive"]);
  const [summary, monitoring, orders, alerts] = await getReportSources(token);
  const equipment = monitoring.data?.equipment ?? [];
  const ids = [...new Set([...equipment.map(row => row.equipment_id), ...(orders.data ?? []).map(row => row.equipment_id)])];
  const records: ReportWindow[] = [];
  const failed: string[] = [];
  for (let i = 0; i < ids.length; i += 6) {
    const batch = await Promise.all(ids.slice(i, i + 6).map(async id => ({ id, result: await getDowntime(id, token) })));
    for (const { id, result } of batch) {
      if (!result.available || !result.data) { failed.push(id); continue; }
      const asset = equipment.find(row => row.equipment_id === id);
      for (const row of result.data) records.push({ ...row, equipment_id: id, station: asset?.station_id ?? "Station not supplied", provenance: typeof asset?.telemetry.provenance === "string" ? asset.telemetry.provenance : "Not supplied" });
    }
  }
  const notices = [
    ...(!summary.available ? ["Network summary unavailable."] : []),
    ...(!monitoring.available ? ["Equipment monitoring unavailable; equipment coverage is incomplete."] : []),
    ...(!orders.available ? ["Work order list unavailable; downtime coverage is incomplete."] : []),
    ...(failed.length ? [`Downtime unavailable for ${failed.length} assets: ${failed.join(", ")}. Totals below are partial.`] : []),
  ];
  return <AppShell user={user}><ReportsWorkspace role={user.role} summary={summary.data} equipment={equipment} monitoringAvailable={monitoring.available} alerts={alerts.data ?? []} alertsAvailable={alerts.available} records={records} notices={notices} asOf={await getRequestTimestamp()} /></AppShell>;
}
