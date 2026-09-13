"use client";

import { useId, useRef, useState } from "react";
import Link from "@/components/navigation-link";
import type { LifecycleEvent } from "@/lib/api";

export function WorkOrderDetail({ id }: { id: string }) {
  const titleId = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const [events, setEvents] = useState<LifecycleEvent[]>([]);
  const [message, setMessage] = useState("");
  async function open() {
    dialog.current?.showModal();
    setMessage("Loading lifecycle…");
    try {
      const response = await fetch(`/api/proxy/maintenance/work-orders/${encodeURIComponent(id)}/lifecycle`);
      if (!response.ok) throw new Error("Lifecycle history is unavailable.");
      const result = await response.json() as LifecycleEvent[];
      setEvents(result);
      setMessage(result.length ? "" : "No lifecycle events returned.");
    } catch (error) { setEvents([]); setMessage(error instanceof Error ? error.message : "Lifecycle unavailable."); }
  }
  return <><button className="panel-link" type="button" onClick={open}>View lifecycle</button><dialog className="lifecycle-drawer" ref={dialog} aria-labelledby={titleId}><div className="detail-actions"><h2 id={titleId}>{id}</h2><button type="button" onClick={() => dialog.current?.close()} aria-label="Close lifecycle">Close</button></div><p role="status">{message}</p><div className="timeline">{events.map(event => <article className="timeline-item" key={event.id}><div><h3>{event.to_status.replaceAll("_", " ")}</h3><p>{event.note}</p><small>{event.actor_role} · {new Date(event.timestamp).toLocaleString()}</small>{event.risk_drivers?.slice(0, 3).map(driver => <p key={driver.feature}>{driver.reason}</p>)}{event.top_features?.slice(0, 3).map(feature => <p key={feature}>{feature}</p>)}</div></article>)}</div><Link href={`/work-orders/${encodeURIComponent(id)}`}>Open full history →</Link></dialog></>;
}
