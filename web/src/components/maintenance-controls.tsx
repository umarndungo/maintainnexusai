"use client";

import { useState, useTransition, type FormEvent, type ReactNode } from "react";
import { ConfirmDialog } from "./confirm-dialog";
import { useRouter } from "next/navigation";
import type { RecentAlert, Technician, WorkOrder } from "@/lib/api";

async function submitOperation(path: string, method: string, body?: object) {
  const response = await fetch(path, { method, headers: { "content-type": "application/json" }, body: body ? JSON.stringify(body) : undefined, credentials: "same-origin" });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = result.detail;
    throw new Error(typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((item: { msg: string }) => item.msg).join("; ") : "The API could not complete this operation.");
  }
  return result;
}

function useMaintenanceOperation() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [pending, transition] = useTransition();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [confirmation, setConfirmation] = useState<{ path: string; method: string; body?: object } | null>(null);
  async function execute(path: string, method: string, body?: object) {
    setBusy(true); setError(""); setMessage("");
    try {
      const result = await submitOperation(path, method, body);
      setMessage(result.work_order_id ? `${result.work_order_id}: ${result.status?.replaceAll("_", " ") ?? "updated"}` : "Updated successfully");
      transition(() => router.refresh());
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Service unavailable. Try again."); }
    finally { setBusy(false); }
  }
  async function run(path: string, method: string, body?: object) { setConfirmation({ path, method, body }); }
  const action = confirmation?.path.split("/").at(-1) ?? "";
  const descriptions: Record<string, string> = { approve: "Approve this work order and dispatch it to the assigned technician.", reject: "Record a rejection. This does not clear equipment alerts or failure conditions.", escalate: "Escalate this pending order for supervisor review.", assign: "Change the assigned maintenance technician for this work order.", start: "Record that maintenance has started on this equipment.", complete: "Complete maintenance and close its recorded downtime window. Sensor readings will remain unchanged." };
  return { run, busy: busy || pending, message, error, confirmation: confirmation ? <ConfirmDialog title="Confirm maintenance action" description={descriptions[action] ?? "Create a work order from this alert and assign the selected technician."} onClose={() => setConfirmation(null)} onConfirm={() => execute(confirmation.path, confirmation.method, confirmation.body)} /> : null };
}

function Feedback({ message, error, confirmation }: { message: string; error: string; confirmation?: ReactNode }) {
  return <>{confirmation}{message && <p className="operation-success" role="status">{message}</p>}{error && <p className="operation-error" role="alert">{error}</p>}</>;
}

function TechnicianSelect({ technicians, cert, current }: { technicians: Technician[]; cert?: string; current?: string }) {
  const eligible = cert ? technicians.filter(tech => tech.on_shift && tech.certs.includes(cert)) : [];
  return <label>Assigned maintenance technician<select name="technician_id" required defaultValue={eligible.some(tech => tech.id === current) ? current : ""}><option value="" disabled>Select an on-shift technician</option>{eligible.map(tech => <option key={tech.id} value={tech.id}>{tech.name} · {tech.active_work_orders} active tasks · {tech.certs.join(", ")}</option>)}</select>{cert && <small>Required certification: {cert}</small>}{!cert ? <small>Required certification is unavailable. Refresh the source alert before assigning.</small> : !eligible.length && <small>No eligible technician is available on shift.</small>}</label>;
}

export function CreateMaintenance({ alert, technicians }: { alert: RecentAlert; technicians: Technician[] }) {
  const operation = useMaintenanceOperation();
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    await operation.run("/api/proxy/maintenance/work-orders", "POST", { equipment_id: alert.equipment_id, alert_task_id: alert.task_id, part_number: alert.part_number, technician_id: data.get("technician_id") });
  }
  if (!alert.task_id || !alert.part_number) return <p className="notice">This alert does not contain the source ID and replacement part required to create maintenance.</p>;
  return <form className="maintenance-form" onSubmit={create}><p>Awaiting maintenance assignment. The automatic pipeline may still be processing this alert.</p><p>Required replacement part: <strong>{alert.part_number}</strong></p><TechnicianSelect technicians={technicians} cert={alert.required_cert} /><button disabled={operation.busy || !alert.required_cert || !technicians.some(tech => tech.on_shift && tech.certs.includes(alert.required_cert!))} type="submit">{operation.busy ? "Creating maintenance…" : "Create task & assign technician"}</button><Feedback {...operation} /></form>;
}

export function MaintenanceControls({ order, technicians, alert, supervisor }: { order: WorkOrder; technicians?: Technician[]; alert?: RecentAlert; supervisor: boolean }) {
  const operation = useMaintenanceOperation();
  const path = `/api/proxy/maintenance/work-orders/${encodeURIComponent(order.work_order_id)}`;
  const review = order.status === "PENDING_APPROVAL" || order.status === "ESCALATED";
  const reassign = review || order.status === "DISPATCHED";
  async function assign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await operation.run(`${path}/assign`, "PATCH", { technician_id: new FormData(event.currentTarget).get("technician_id") });
  }
  return <div className="maintenance-controls">{reassign && (technicians ? <form className="maintenance-form" onSubmit={assign}><TechnicianSelect technicians={technicians} cert={alert?.required_cert} current={order.assigned_technician_id} /><button type="submit" disabled={operation.busy || !alert?.required_cert || !technicians.some(tech => tech.on_shift && tech.certs.includes(alert.required_cert!))}>{operation.busy ? "Updating…" : "Update assignment"}</button></form> : <p className="notice">Technician roster unavailable; assignment choices cannot be confirmed.</p>)}<div className="maintenance-actions">{review && <><button disabled={operation.busy} onClick={() => operation.run(`${path}/approve`, "PATCH")}>Approve & dispatch</button><button className="secondary-button" disabled={operation.busy} onClick={() => operation.run(`${path}/reject`, "PATCH")}>Reject</button>{supervisor && order.status === "PENDING_APPROVAL" && <button className="secondary-button" disabled={operation.busy} onClick={() => operation.run(`${path}/escalate`, "PATCH")}>Escalate</button>}</>}{order.status === "DISPATCHED" && <button disabled={operation.busy} onClick={() => operation.run(`${path}/start`, "PATCH")}>Start maintenance</button>}{order.status === "IN_PROGRESS" && <button disabled={operation.busy} onClick={() => operation.run(`${path}/complete`, "PATCH")}>Complete maintenance</button>}</div>{order.status === "COMPLETED" && <p className="operation-success">Maintenance completed. Check a fresh sensor reading to verify equipment recovery.</p>}{order.status === "REJECTED" && <p>Task rejected. This does not clear the equipment failure condition.</p>}<Feedback {...operation} /></div>;
}
