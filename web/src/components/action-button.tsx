"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ConfirmDialog } from "./confirm-dialog";

type ActionButtonProps = {
  workOrderId: string;
  action: "approve" | "reject" | "escalate";
};

const labels = {
  approve: "Approve",
  reject: "Reject",
  escalate: "Escalate",
};

export function ActionButton({ workOrderId, action }: ActionButtonProps) {
  const router = useRouter();
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [confirm, setConfirm] = useState(false);

  async function handleAction() {
    setState("loading");
    try {
      const response = await fetch(`/api/proxy/maintenance/work-orders/${encodeURIComponent(workOrderId)}/${action}`, {
        method: "PATCH",
        credentials: "same-origin",
      });
      if (!response.ok) {
        setState("error");
        return;
      }
      setState("done");
      router.refresh();
    } catch {
      setState("error");
    }
  }

  return <><button className={`action action-${action}`} disabled={state === "loading" || state === "done"} onClick={() => setConfirm(true)} type="button" title={state === "error" ? "The server rejected this action. Try again." : labels[action]}>{state === "loading" ? "Working..." : state === "done" ? "Updated" : state === "error" ? "Retry" : labels[action]}</button>{state === "error" && <span role="alert">The server rejected this action. Retry when ready.</span>}{confirm && <ConfirmDialog title={`${labels[action]} ${workOrderId}?`} description={action === "approve" ? "This approves the work order and dispatches it to the assigned technician." : action === "reject" ? "This records a rejection. It does not clear the equipment failure condition." : "This escalates the work order for supervisor review."} onConfirm={handleAction} onClose={() => setConfirm(false)} />}</>;
}
