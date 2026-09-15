// Uses the running backend and persisted records; no mocked API.
import assert from "node:assert/strict";
import { summarizeWindows, reportCsv, csvCell } from "../src/lib/report-data.ts";
const app = process.env.APP_URL ?? "http://localhost:3001";
const api = process.env.API_BASE_URL ?? "http://localhost:8000";
for (const role of ["supervisor", "executive", "engineer"]) {
  const login = await fetch(app + "/api/auth/login", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ user_id: `${role}-demo` }) });
  assert.equal(login.status, 200);
  const cookie = login.headers.get("set-cookie").split(";")[0];
  const response = await fetch(app + "/reports", { headers: { cookie }, redirect: "manual" });
  const html = await response.text();
  if (role === "engineer") assert.ok(response.headers.get("location") === "/dashboard" || html.includes("url=/dashboard") || html.includes("NEXT_REDIRECT;replace;/dashboard"));
  else {
    assert.equal(response.status, 200);
    for (const text of ["Downtime Trend", "Downtime by Site", "Network Downtime Records", "Export Report", "Export to CSV", "Network availability"]) assert.ok(html.includes(text), text);
    assert.ok(!html.includes("99.7%"));
  }
  await fetch(app + "/api/auth/logout", { method: "POST", headers: { cookie } });
  console.log(`PASS ${role} reports access`);
}
const login = await fetch(api + "/api/v1/auth/login", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ user_id: "supervisor-demo" }) });
assert.equal(login.status, 200);
const { access_token } = await login.json();
async function get(path) {
  const r = await fetch(api + "/api/v1" + path, { headers: { authorization: `Bearer ${access_token}` } });
  assert.equal(r.status, 200, path); return r.json();
}
const [monitoring, orders] = await Promise.all([get("/monitoring/equipment"), get("/maintenance/work-orders")]);
const records = [];
for (const id of new Set([...monitoring.equipment.map(row => row.equipment_id), ...orders.map(row => row.equipment_id)])) {
  const windows = await get(`/dashboard/equipment/${encodeURIComponent(id)}/downtime`);
  for (const row of windows) records.push({ ...row, equipment_id: id, station: monitoring.equipment.find(asset => asset.equipment_id === id)?.station_id ?? "Station not supplied", provenance: "Not supplied" });
}
for (const days of [7, 30, 90]) {
  const result = summarizeWindows(records, days, Date.now());
  const total = result.rows.reduce((sum, row) => sum + row.period_minutes, 0);
  assert.ok(Math.abs(result.daily.reduce((sum, row) => sum + row.minutes, 0) - total) < .00001);
  assert.ok(Math.abs(result.sites.reduce((sum, [, minutes]) => sum + minutes, 0) - total) < .00001);
  assert.ok(result.rows.every(row => row.period_minutes >= 0));
  const csv = reportCsv(result.rows, [["Period", days]]);
  assert.ok(csv.startsWith("\uFEFF"));
  assert.ok(csv.includes('"Minutes within selected period"'));
  for (const row of result.rows) assert.ok(csv.includes(csvCell(row.equipment_id)));
  console.log(`PASS ${days}-day aggregation and CSV: ${result.rows.length} persisted windows`);
}
assert.equal(csvCell('=1+1'), '"\'=1+1"');
assert.equal(csvCell('a,"b"'), '"a,""b"""');
console.log("PASS spreadsheet formula escaping and CSV quoting");
