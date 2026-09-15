"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export function LiveUpdates() {
  const router = useRouter();
  const [status, setStatus] = useState("Connecting to live events");
  const [alertEquipment, setAlertEquipment] = useState<string | null>(null);
  useEffect(() => {
    const events = new EventSource("/api/events");
    let refreshTimer: ReturnType<typeof setTimeout> | undefined;
    const refresh = () => {
      // Coalesce bursts of pushed events; this is not a polling timer.
      if (refreshTimer) return;
      refreshTimer = setTimeout(() => { refreshTimer = undefined; router.refresh(); }, 300);
    };
    const ready = () => { setStatus("Live updates connected"); refresh(); };
    events.addEventListener("ready", ready);
    events.onmessage = refresh;
    events.addEventListener("alert.created", (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        if (typeof data.equipment_id === "string") setAlertEquipment(data.equipment_id);
      } catch { /* A malformed event must not interrupt reconnection. */ }
    });
    for (const name of ["work_order.lifecycle", "alert.created", "telemetry.received", "update"]) events.addEventListener(name, refresh);
    events.onerror = () => setStatus("Live updates unavailable — reconnecting");
    // EventSource reconnects automatically; readiness also reloads data missed offline.
    return () => { events.close(); if (refreshTimer) clearTimeout(refreshTimer); };
  }, [router]);
  return <><span className="live-status" data-state={status === "Live updates connected" ? "connected" : "reconnecting"} role="status">{status}</span>{alertEquipment && <div className="failure-notification" role="alert"><strong>New equipment failure alert</strong><span>{alertEquipment} requires attention. The alert details are updating.</span><button type="button" onClick={() => setAlertEquipment(null)} aria-label="Dismiss failure notification">Dismiss</button></div>}</>;
}

