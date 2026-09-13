import type { LifecycleEvent } from "@/lib/api";

export function LifecycleEvidence({ event }: { event: LifecycleEvent }) {
  return <>
    {event.from_status && <p>{event.from_status === event.to_status ? "Status unchanged; handoff recorded" : `${event.from_status.replaceAll("_", " ")} → ${event.to_status.replaceAll("_", " ")}`}</p>}
    {event.event_hash && <details><summary>Recorded chain references</summary><dl className="prediction-evidence"><div><dt>Event hash</dt><dd>{event.event_hash}</dd></div><div><dt>Previous event hash</dt><dd>{event.previous_event_hash ?? "Not supplied"}</dd></div></dl><p>These are backend-recorded hashes. Displaying them does not verify the chain.</p></details>}
  </>;
}
