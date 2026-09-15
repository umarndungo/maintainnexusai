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
    let refreshing = false;
    let closed = false;
    const refresh = () => {
      // Coalesce bursts of pushed events; this is not a polling timer.
      if (refreshTimer || refreshing) return;
      refreshTimer = setTimeout(async () => {
        refreshTimer = undefined;
        refreshing = true;
        try {
          const response = await fetch("/api/auth/session", { cache: "no-store" });
          if (closed) return;
          if (response.ok) { setStatus("Live updates connected"); router.refresh(); }
          else setStatus(response.status === 401 ? "Session expired — sign in again" : "Connection interrupted — showing last loaded data");
        } catch {
          if (!closed) setStatus("Connection interrupted — showing last loaded data");
        } finally { refreshing = false; }
      }, 1000);
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
    return () => { closed = true; events.close(); if (refreshTimer) clearTimeout(refreshTimer); };
  }, [router]);
  return <><span className="live-status" data-state={status === "Live updates connected" ? "connected" : "reconnecting"} role="status">{status}</span>{alertEquipment && <div className="failure-notification" role="alert"><strong>New equipment failure alert</strong><span>{alertEquipment} requires attention. The alert details are updating.</span><button type="button" onClick={() => setAlertEquipment(null)} aria-label="Dismiss failure notification">Dismiss</button></div>}</>;
}

