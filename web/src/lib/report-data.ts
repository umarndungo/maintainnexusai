export type ReportWindow = {
  id: number; equipment_id: string; station: string; work_order_id?: string;
  started_at: string; ended_at?: string | null; duration_seconds?: number;
  cause_alert_id?: string | null; provenance: string;
};

export function summarizeWindows(records: ReportWindow[], days: number, asOf: number) {
  const day = 86400000;
  const start = Math.floor(asOf / day) * day - (days - 1) * day;
  const daily = Array.from({ length: days }, (_, i) => ({ time: start + i * day, minutes: 0 }));
  const sites = new Map<string, number>();
  const rows: Array<ReportWindow & { period_minutes: number }> = [];
  let omitted = 0;
  for (const row of records) {
    const from = Date.parse(row.started_at);
    const to = row.ended_at ? Date.parse(row.ended_at) : typeof row.duration_seconds === "number" ? from + row.duration_seconds * 1000 : NaN;
    if (!Number.isFinite(from) || !Number.isFinite(to) || to < from) { omitted++; continue; }
    const a = Math.max(start, from), b = Math.min(asOf, to);
    if (b < a || to < start || from > asOf) continue;
    const minutes = (b - a) / 60000;
    rows.push({ ...row, period_minutes: minutes });
    sites.set(row.station, (sites.get(row.station) ?? 0) + minutes);
    for (const bucket of daily) bucket.minutes += Math.max(0, Math.min(b, bucket.time + day) - Math.max(a, bucket.time)) / 60000;
  }
  rows.sort((a, b) => Date.parse(b.started_at) - Date.parse(a.started_at));
  return { rows, daily, sites: [...sites].sort((a, b) => b[1] - a[1]), omitted, start };
}

export function csvCell(value: unknown) {
  const text = value == null ? "" : String(value);
  const safe = /^[\s]*[=+@-]/.test(text) ? `'${text}` : text;
  return `"${safe.replaceAll('"', '""')}"`;
}

export function reportCsv(rows: Array<ReportWindow & { period_minutes: number }>, metadata: Array<[string, string | number]>) {
  const lines: unknown[][] = [["MaintainNexus network downtime report"], ...metadata, [],
    ["ID", "Equipment", "Station", "Work order", "Cause alert ID", "Start UTC", "End UTC", "Recorded duration seconds", "Minutes within selected period", "Status", "Latest equipment provenance"],
    ...rows.map(row => [row.id, row.equipment_id, row.station, row.work_order_id, row.cause_alert_id, row.started_at, row.ended_at, row.duration_seconds, row.period_minutes, row.ended_at ? "Closed" : "Open", row.provenance])];
  return "\uFEFF" + lines.map(line => line.map(csvCell).join(",")).join("\r\n");
}
