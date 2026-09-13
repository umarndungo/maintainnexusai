"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export function LiveUpdates() {
  const router = useRouter();
  const [status, setStatus] = useState("Connecting to live events");
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
    for (const name of ["work_order.lifecycle", "alert.created", "update"]) events.addEventListener(name, refresh);
    events.onerror = () => setStatus("Live updates unavailable — reconnecting");
    // EventSource reconnects automatically; readiness also reloads data missed offline.
    return () => { events.close(); if (refreshTimer) clearTimeout(refreshTimer); };
  }, [router]);
  return <span className="live-status" role="status">{status}</span>;
}
