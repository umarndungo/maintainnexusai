// Integration checks against a test-only API. No mock path exists in the application.
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { setTimeout as delay } from "node:timers/promises";

const seen = [];
const prediction = { failure_probability: .2, failure_predicted: true, risk_level: "MEDIUM", threshold: .12, prediction_horizon_hours: 6 };
const thresholds = { failure_probability: .12, warning_probability: null, prediction_horizon_hours: 6, source: "saved model", sensor_limits: null };
const equipmentReading = { id: 1, equipment_id: "PUMP-101", station_id: "STATION-1", telemetry: { temperature_c: 95, vibration_mm_s: 5, timestamp: "2026-09-01T00:00:00Z" }, prediction, state: "FAILURE_DETECTED", received_at: "2026-09-01T00:00:01Z" };
let executiveShape = "current";
const mock = createServer(async (req, res) => {
  let text = "";
  for await (const chunk of req) text += chunk;
  const data = text ? JSON.parse(text) : {};
  seen.push({ path: req.url, method: req.method, authorization: req.headers.authorization, data });
  const role = req.headers.authorization?.replace("Bearer test-", "");
  const reply = (body, status = 200) => { res.writeHead(status, { "content-type": "application/json" }); res.end(JSON.stringify(body)); };
  if (req.url === "/api/v1/auth/login") return reply({ access_token: `test-${data.user_id.replace("-demo", "")}` });
  if (req.url === "/api/v1/auth/me") {
    if (role === "expired") return reply({}, 401);
    if (role === "offline") return reply({}, 503);
    return reply({ id: `${role}-demo`, role, station_ids: ["STATION-1"] });
  }
  if (req.url === "/api/v1/events") {
    res.writeHead(200, { "content-type": "text/event-stream" });
    res.write("event: ready\ndata: {}\n\n");
    return;
  }
  if (req.url === "/api/v1/monitoring/equipment") return reply({ equipment: [equipmentReading], thresholds, source: "Persisted telemetry" });
  if (req.url.endsWith("/history")) return reply({ readings: [{ ...equipmentReading, id: 0, telemetry: { ...equipmentReading.telemetry, temperature_c: 90, timestamp: "2026-08-31T23:59:00Z" } }, equipmentReading], thresholds });
  if (req.url === "/api/v1/hr/technicians/available") return reply({ available_technicians: [{ id: "TECH-101", name: "Alice", certs: ["HVAC"], on_shift: true, active_work_orders: 1 }], source: "HR roster" });
  if (req.url === "/api/v1/dashboard/summary") return reply({ open_work_orders: 1, alert_count: 1, uptime_percentage: 99, recent_health_checks: [{ equipment_id: "PUMP-101", health_status: "NORMAL", checked_at: new Date().toISOString() }] });
  if (req.url === "/api/v1/maintenance/work-orders" && req.method === "GET") return reply([
    { work_order_id: "WO-PENDING", equipment_id: "PUMP-101", status: "PENDING_APPROVAL", assigned_technician_id: "TECH-101", alert_task_id: "ALERT-1" },
    { work_order_id: "WO-ESCALATED", equipment_id: "PUMP-101", status: "ESCALATED" },
  ]);
  if (req.url === "/api/v1/dashboard/audit-logs") return reply([{ id: 1, event_name: "ALERT_RECEIVED", payload: "{}", timestamp: new Date().toISOString() }]);
  if (req.url === "/api/v1/dashboard/audit-logs/verify") return reply({}, 404);
  if (req.url === "/api/v1/dashboard/executive-summary") return reply(executiveShape === "current" ? { downtime_minutes: 42, open_windows: 1, completed_windows: 0, uptime_trend: "stable" } : { downtime_avoided_minutes: 123, cost_saved: 456, uptime_trend: [{ date: "2026-09-01", uptime: 99 }], station_comparison: [{ station_id: "STATION-1", uptime: 99 }] });
  if (req.url === "/api/v1/alerts/recent") return reply([{ task_id: "ALERT-1", equipment_id: "PUMP-101", severity: "HIGH", failure_code: "ERR_TEST", prediction, telemetry: equipmentReading.telemetry, part_number: "Seal", required_cert: "HVAC" }]);
  if (req.url === "/api/v1/hse/overview") return reply({}, 404);
  if (req.url.endsWith("/lifecycle")) return reply([{ id: 1, to_status: "PENDING_APPROVAL", actor_id: "system", actor_role: "internal", timestamp: new Date().toISOString() }]);
  if (req.url.endsWith("/downtime")) return reply([]);
  return reply({ status: "DISPATCHED" });
});

mock.listen(0, "127.0.0.1");
await once(mock, "listening");
const reservation = createServer();
reservation.listen(0, "127.0.0.1");
await once(reservation, "listening");
const port = reservation.address().port;
await new Promise(resolve => reservation.close(resolve));
const base = `http://127.0.0.1:${port}`;
const app = spawn(process.execPath, ["node_modules/next/dist/bin/next", "start", "--port", String(port)], {
  cwd: process.cwd(),
  env: { ...process.env, API_BASE_URL: `http://127.0.0.1:${mock.address().port}`, NEXT_TELEMETRY_DISABLED: "1" },
  stdio: ["ignore", "pipe", "pipe"],
});
let log = "";
app.stdout.on("data", chunk => { log += chunk; });
app.stderr.on("data", chunk => { log += chunk; });
const request = (path, cookie, options = {}) => fetch(base + path, { ...options, headers: { ...(cookie ? { cookie } : {}), ...options.headers }, redirect: "manual" });
async function expectRedirect(response, expected) {
  // Next.js may stream a redirect as a meta/RSC instruction with HTTP 200.
  const location = response.headers.get("location");
  if (location) { assert.ok(location.startsWith(expected), location); return; }
  const html = await response.text();
  assert.ok(html.includes(`NEXT_REDIRECT;replace;${expected}`) || html.includes(`url=${expected}`), `Expected redirect to ${expected}`);
}
const session = role => `maintainnexus_token=test-${role}`;
try {
  let ready = false;
  for (let i = 0; i < 100; i++) {
    if (app.exitCode !== null) throw new Error(log);
    try { if ((await request("/login")).ok) { ready = true; break; } } catch {}
    await delay(200);
  }
  assert.ok(ready, `Next.js failed to start: ${log}`);
  await expectRedirect(await request("/dashboard"), "/login");
  const login = await request("/api/auth/login", undefined, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ user_id: "engineer-demo" }) });
  assert.equal(login.status, 200);
  assert.match(login.headers.get("set-cookie"), /HttpOnly/i);
  assert.match(login.headers.get("set-cookie"), /Max-Age=3600/);
  assert.equal((await login.json()).access_token, undefined);
  const cookie = login.headers.get("set-cookie").split(";")[0];
  const dashboard = await (await request("/dashboard", cookie)).text();
  assert.ok(dashboard.includes("WO-PENDING") && dashboard.includes("ERR_TEST"));
  assert.ok(seen.some(item => item.path === "/api/v1/auth/me" && item.authorization === "Bearer test-engineer"));
  const monitor = await (await request("/equipment", cookie)).text();
  assert.ok(monitor.includes("Failure risk detected") && monitor.includes("12.0%") && monitor.includes("95"));
  const equipment = await (await request("/equipment/PUMP-101", cookie)).text();
  assert.ok(equipment.includes("sensor-chart") && equipment.includes("TECH-101") && equipment.includes("Approve &amp; dispatch"));
  assert.ok(equipment.includes("Complete") || equipment.includes("repair progress"));
  assert.equal((await request("/api/proxy/maintenance/work-orders/WO-PENDING/start", session("executive"), { method: "PATCH" })).status, 403);
  assert.equal((await request("/api/proxy/maintenance/work-orders/WO-PENDING/assign", cookie, { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ technician_id: "TECH-101" }) })).status, 200);
  assert.ok(seen.some(item => item.path.endsWith("/assign") && item.data.technician_id === "TECH-101" && item.authorization === "Bearer test-engineer"));
  const filtered = await (await request("/dashboard?status=ESCALATED", cookie)).text();
  assert.ok(filtered.includes("WO-ESCALATED"));
  // The queue excludes pending rows; historical alert handoffs remain visible.
  const filteredQueue = filtered.split('<article class="panel" id="work-orders">')[1].split('</article>')[0];
  assert.ok(!filteredQueue.includes('href="/work-orders/WO-PENDING"'));
  assert.ok(filteredQueue.includes('href="/work-orders/WO-ESCALATED"'));
  const count = seen.filter(item => item.path === "/api/v1/dashboard/summary").length;
  await expectRedirect(await request("/dashboard", session("technician")), "/access-denied");
  await expectRedirect(await request("/dashboard", session("executive")), "/executive");
  assert.equal(seen.filter(item => item.path === "/api/v1/dashboard/summary").length, count);
  await expectRedirect(await request("/dashboard", session("expired")), "/login");
  await expectRedirect(await request("/dashboard", session("offline")), "/session-unavailable");
  const action = "/api/proxy/maintenance/work-orders/WO-PENDING/approve";
  assert.equal((await request(action, undefined, { method: "PATCH" })).status, 401);
  assert.equal((await request(action, session("executive"), { method: "PATCH" })).status, 403);
  assert.equal((await request(action, cookie, { method: "PATCH", headers: { authorization: "Bearer forged" } })).status, 200);
  assert.equal(seen.findLast(item => item.path.endsWith("/approve")).authorization, "Bearer test-engineer");
  assert.equal((await request("/api/proxy/maintenance/work-orders/WO-PENDING/escalate", cookie, { method: "PATCH" })).status, 403);
  assert.equal((await request("/api/proxy/maintenance/work-orders/WO-PENDING/escalate", session("supervisor"), { method: "PATCH" })).status, 200);
  assert.ok((await (await request("/dashboard", session("supervisor"))).text()).includes("Supervisor escalation queue"));
  assert.equal((await request("/api/proxy/maintenance/work-orders/WO-PENDING/lifecycle", cookie)).status, 200);
  const audit = await (await request("/audit", cookie)).text();
  assert.ok(audit.includes("Verification unavailable") && audit.includes("ALERT RECEIVED"));
  const executive = await (await request("/executive", session("executive"))).text();
  assert.ok(executive.includes("Recorded downtime") && executive.includes("stable"));
  executiveShape = "planned";
  const planned = await (await request("/executive", session("executive"))).text();
  assert.ok(planned.includes("123m") && planned.includes("456") && planned.includes("uptime-chart"));
  const streamAbort = new AbortController();
  const stream = await request("/api/events", cookie, { signal: streamAbort.signal });
  assert.match(stream.headers.get("content-type"), /text\/event-stream/);
  const reader = stream.body.getReader();
  assert.match(new TextDecoder().decode((await reader.read()).value), /event: ready/);
  streamAbort.abort();
  assert.equal((await request("/api/auth/logout", cookie, { method: "POST" })).status, 200);
  console.log("Frontend smoke checks passed: login, role guards, filters, cookie actions, SSE, and current/planned contracts.");
} finally {
  if (process.platform === "win32") {
    const stop = spawn("taskkill", ["/pid", String(app.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    stop.unref();
  } else app.kill();
  app.unref();
  app.stdout.destroy();
  app.stderr.destroy();
  mock.closeAllConnections();
  mock.close();
  mock.unref();
}
