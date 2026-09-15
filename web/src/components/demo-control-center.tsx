"use client";

import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

type Action = "telemetry" | "overfill" | "work-order";
const actions: Record<Action, { label: string; detail: string }> = {
  telemetry: { label: "Send sample sensor reading", detail: "Submits a legacy sample reading; it lacks the history required for ML scoring" },
  overfill: { label: "Trigger overfill warning", detail: "Assesses a simulated tank fill; no equipment commands" },
  "work-order": { label: "Assign alert maintenance", detail: "Open alert assignment in the equipment workflow" },
};

export function DemoControlCenter() {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<Action | null>(null);
  const [message, setMessage] = useState("");
  const [stationId, setStationId] = useState("");
  if (pathname !== "/dashboard" && pathname !== "/supervisor") return null;

  async function run(action: Action) {
    if (action === "work-order") {
      router.push("/equipment");
      return;
    }
    setBusy(action);
    setMessage("");
    const bodies = {
      telemetry: { ...(stationId.trim() ? { station_id: stationId.trim() } : {}), equipment_id: "PUMP-101", temperature: 108, vibration: 6.4, installation_age_hours: 14500, timestamp: new Date().toISOString() },
      overfill: { tank_id: "TANK-04", level_percent: 91, flow_rate_lpm: 1280, safe_level_percent: 85, max_flow_rate_lpm: 1200, capacity_liters: 50000 },
      "work-order": { equipment_id: "PUMP-101", technician_id: "TECH-101", part_number: "Pump Seal Kit #A4" },
    };
    const paths = { telemetry: "/api/proxy/alerts/telemetry", overfill: "/api/proxy/hse/overfill-risk", "work-order": "/api/proxy/maintenance/work-orders" };
    try {
      const response = await fetch(paths[action], { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(bodies[action]) });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "The backend rejected this demo action.");
      setMessage(action === "overfill" ? `Simulated assessment: ${result.severity}. ${result.recommended_action}` : result.status === "duplicate" ? "Duplicate sensor timestamp; the backend did not create another reading or alert." : result.prediction ? `Backend prediction: ${(result.prediction.failure_probability * 100).toFixed(1)}% risk against ${(result.prediction.threshold * 100).toFixed(1)}%. ${result.alert_created ? result.maintenance_queued ? "Alert saved and maintenance queued." : "Alert saved; maintenance was not queued." : "The model did not predict failure."}` : result.evaluation_reason ?? "Reading accepted without a compatible model evaluation; equipment health has not been established.");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  return <aside className={`demo-center ${open ? "is-open" : ""}`}><button className="demo-center-toggle" onClick={() => setOpen((value) => !value)} type="button"><span className="demo-live-dot" />Demo control center <b>{open ? "-" : "+"}</b></button>{open && <div className="demo-center-panel"><span className="eyebrow">JUDGE MODE / LIVE ACTIONS</span><h2>Make the story move.</h2><p>Submit sample data to the backend. Tank assessments are simulated and do not control equipment.</p><label className="demo-station">Station ID for sample reading<input value={stationId} onChange={event => setStationId(event.target.value)} placeholder="Equipment station ID" /><small>Provide the equipment’s station. A single-station engineer session may infer it; supervisors must supply it.</small></label>{(Object.keys(actions) as Action[]).map((action) => <button className="demo-action" disabled={busy !== null} key={action} onClick={() => run(action)} type="button"><span><strong>{busy === action ? "Working..." : actions[action].label}</strong><small>{actions[action].detail}</small></span><b>-&gt;</b></button>)}{message && <div className="demo-result">{message}</div>}</div>}</aside>;
}
