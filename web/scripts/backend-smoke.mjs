// Exercise Next.js against the actual API, trained model and isolated database.
import assert from "node:assert/strict";
import { createServer } from "node:net";
import { once } from "node:events";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";

async function reservePort() {
  const server = createServer();
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const port = server.address().port;
  await new Promise(resolve => server.close(resolve));
  return port;
}

const backendPort = await reservePort();
const frontendPort = await reservePort();
const backendBase = `http://127.0.0.1:${backendPort}`;
const frontendBase = `http://127.0.0.1:${frontendPort}`;
const processes = [];
const logs = [];
function launch(command, args, env) {
  const child = spawn(command, args, { cwd: process.cwd(), env: { ...process.env, ...env }, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
  const entry = { child, output: "" };
  processes.push(child);
  logs.push(entry);
  child.stdout.on("data", chunk => { entry.output += chunk; });
  child.stderr.on("data", chunk => { entry.output += chunk; });
  child.on("error", error => { entry.output += error.message; });
  return child;
}

const backend = launch(process.env.PYTHON ?? "python", ["../tests/frontend_contract_server.py", String(backendPort)], {
  DATABASE_URL: "sqlite://", AUTH_SECRET: "frontend-contract-test", INTERNAL_SERVICE_TOKEN: "frontend-contract-service",
  API_BASE_URL: backendBase, API_INTERNAL_BASE_URL: `${backendBase}/api/v1`, ML_API_BASE_URL: `${backendBase}/api/v1`,
  ML_SCORING_MODE: "http", RISK_WARNING_THRESHOLD: "", SIMULATED_STATION_ID: "",
});
const frontend = launch(process.execPath, ["node_modules/next/dist/bin/next", "start", "--port", String(frontendPort)], {
  API_BASE_URL: `${backendBase}/api/v1`, NEXT_TELEMETRY_DISABLED: "1",
});
const request = (path, cookie, options = {}) => fetch(frontendBase + path, { ...options, headers: { ...(cookie ? { cookie } : {}), ...options.headers }, redirect: "manual" });
async function ready(url, child) {
  for (let attempt = 0; attempt < 150; attempt++) {
    if (child.exitCode !== null) throw new Error(logs.find(entry => entry.child === child).output);
    try { if ((await fetch(url)).ok) return; } catch {}
    await delay(200);
  }
  throw new Error(`Server did not become ready: ${logs.find(entry => entry.child === child).output}`);
}
async function login(userId) {
  const response = await request("/api/auth/login", undefined, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ user_id: userId }) });
  assert.equal(response.status, 200);
  assert.match(response.headers.get("set-cookie"), /HttpOnly/);
  return response.headers.get("set-cookie").split(";")[0];
}
async function action(path, cookie, body) {
  const response = await request(path, cookie, { method: body ? "POST" : "PATCH", headers: { "content-type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  const result = await response.json();
  assert.ok(response.ok, `${response.status}: ${JSON.stringify(result)}`);
  return result;
}

try {
  await Promise.all([ready(`${backendBase}/openapi.json`, backend), ready(`${frontendBase}/login`, frontend)]);
  const engineer = await login("engineer-demo");
  const executive = await login("executive-demo");
  const sample = await (await fetch(`${backendBase}/__test/reading`)).json();
  const result = await action("/api/proxy/alerts/telemetry", engineer, sample);
  assert.equal(result.prediction.threshold, .12);
  assert.equal(result.prediction.target, "failure_next_6h");
  assert.equal(result.prediction.failure_predicted, true);
  assert.equal(result.alert_created, true);
  assert.equal(result.maintenance_queued, true);
  assert.ok(result.prediction.prediction_id);
  const equipment = await (await request("/equipment/PUMP-001", engineer)).text();
  assert.ok(equipment.includes(`${(result.prediction.failure_probability * 100).toFixed(1)}%`));
  assert.ok(equipment.includes(result.prediction.model_version));
  assert.ok(equipment.includes(result.prediction.prediction_id));
  assert.ok(equipment.includes("Global model feature importance"));
  assert.ok(equipment.includes("do not explain this individual prediction"));
  assert.ok(equipment.includes("Create task &amp; assign technician"));
  const token = engineer.slice("maintainnexus_token=".length);
  const getBackend = path => fetch(`${backendBase}/api/v1${path}`, { headers: { authorization: `Bearer ${token}` } }).then(response => response.json());
  const [alerts, roster] = await Promise.all([getBackend("/alerts/recent"), getBackend("/hr/technicians/available")]);
  const alert = alerts.find(item => item.task_id === result.task_id);
  const technician = roster.available_technicians.find(item => item.on_shift && item.certs.includes(alert.required_cert));
  assert.ok(technician, "Fixture must contain an eligible on-shift technician");
  const order = await action("/api/proxy/maintenance/work-orders", engineer, { equipment_id: alert.equipment_id, alert_task_id: alert.task_id, part_number: alert.part_number, technician_id: technician.id });
  const orderPath = `/api/proxy/maintenance/work-orders/${order.work_order_id}`;
  assert.equal((await action(`${orderPath}/approve`, engineer)).status, "DISPATCHED");
  let orderPage = await (await request(`/work-orders/${order.work_order_id}`, engineer)).text();
  assert.ok(orderPage.includes("Start maintenance") && orderPage.includes("Recorded chain references"));
  assert.ok(orderPage.includes(result.prediction.prediction_id));
  assert.equal((await action(`${orderPath}/start`, engineer)).status, "IN_PROGRESS");
  orderPage = await (await request(`/work-orders/${order.work_order_id}`, engineer)).text();
  assert.ok(orderPage.includes("Complete maintenance"));
  assert.equal((await action(`${orderPath}/complete`, engineer)).status, "COMPLETED");
  const repaired = await (await request("/equipment/PUMP-001", engineer)).text();
  assert.ok(repaired.includes("Maintenance completed") && repaired.includes("Failure risk detected"));
  const executiveEquipment = await (await request("/equipment/PUMP-001", executive)).text();
  assert.ok(executiveEquipment.includes("Failure risk detected"));
  assert.ok(!executiveEquipment.includes(">Approve &amp; dispatch</button>") && !executiveEquipment.includes(">Start maintenance</button>"));
  assert.equal((await request(`${orderPath}/start`, executive, { method: "PATCH" })).status, 403);
  const dashboard = await (await request("/dashboard", engineer)).text();
  assert.ok(dashboard.includes("Simulated uptime") && dashboard.includes("Simulated downtime") && dashboard.includes("Summary metrics cover the backend dataset"));
  const executivePage = await (await request("/executive", executive)).text();
  assert.ok(executivePage.includes("Recorded downtime") && executivePage.includes("Completed downtime windows"));
  assert.ok(!executivePage.includes("<span>Cost saved</span>"));
  assert.ok(executivePage.includes("does not calculate avoided downtime or cost savings"));
  const audit = await (await request("/audit", engineer)).text();
  assert.ok(audit.includes("Verification unavailable") && !audit.includes("<h2>Chain verified</h2>"));
  assert.ok(audit.includes("latest 50 backend audit records"));
  const monitoring = await (await request("/equipment", executive)).text();
  assert.ok(monitoring.includes("Approaching threshold (not configured)"));
  console.log("Real backend/frontend checks passed: trained ML HTTP scoring, prediction evidence, alert assignment, repair lifecycle, downtime, executive read-only access and truthful summary/audit states.");
} finally {
  for (const child of processes) {
    if (!child.pid) continue;
    if (process.platform === "win32") {
      const stop = spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
      await once(stop, "exit");
    } else child.kill();
    child.stdout.destroy(); child.stderr.destroy(); child.unref();
  }
}
