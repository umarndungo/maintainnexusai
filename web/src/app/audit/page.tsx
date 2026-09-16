import { workspacePath } from "@/lib/workspace";
import { ApiNotice } from "@/components/api-notice";
import Link from "@/components/navigation-link";
import { requireSession } from "@/lib/session";
import { getAuditLogs, getAuditVerification } from "@/lib/api";
import { AppShell } from "@/components/app-shell";


const PAGE_SIZE = 15;

export default async function AuditPage({ searchParams }: { searchParams: Promise<{ event?: string; from?: string; to?: string; page?: string }> }) {
  const { token, user } = await requireSession(["engineer", "supervisor", "executive"]);
  const { event = "", from = "", to = "", page: pageParam = "1" } = await searchParams;
  const [result, logsResult] = await Promise.all([getAuditVerification(), getAuditLogs(token)]);
  const verification = result.data;
  const logs = logsResult.data ?? [];
  const start = from ? Date.parse(`${from}T00:00:00Z`) : -Infinity;
  const end = to ? Date.parse(`${to}T23:59:59.999Z`) : Infinity;
  const filtered = logs.filter(log => (!event || log.event_name === event) && Date.parse(log.timestamp) >= start && Date.parse(log.timestamp) <= end);
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(Math.max(1, parseInt(pageParam, 10) || 1), totalPages);
  const paged = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);
  const pageHref = (target: number) => {
    const params = new URLSearchParams();
    if (event) params.set("event", event);
    if (from) params.set("from", from);
    if (to) params.set("to", to);
    if (target > 1) params.set("page", String(target));
    const qs = params.toString();
    return `/audit${qs ? `?${qs}` : ""}`;
  };
  const state = !verification ? "unavailable" : verification.chain_integrity ? "valid" : "invalid";
  return <AppShell user={user}><main className="detail-shell"><header className="detail-header"><div><span className="eyebrow">TRACEABILITY / INTEGRITY</span><h1>Audit chain</h1><p>Read-only records and the backend verification result.</p></div><div className="detail-actions"><Link href={workspacePath(user.role)}>Back to workspace</Link></div></header><section className={`integrity-hero integrity-${state}`}><span className="integrity-symbol">{state === "valid" ? "?" : state === "invalid" ? "!" : "?"}</span><div><span className="eyebrow">{verification?.chain ?? "Audit chain"}</span><h2>{state === "valid" ? "Chain verified" : state === "invalid" ? "Verification failed" : "Verification unavailable"}</h2><p>{verification ? `${verification.checked_events} events checked at ${new Date(verification.verified_at).toLocaleString()}.` : "The backend has not returned a verification result. This does not establish that the chain passed or failed."}</p></div></section><ApiNotice result={result} label="Audit verification unavailable" /><section className="detail-panel"><h2>Audit records</h2><p className="monitoring-context">This endpoint returns the latest 50 backend audit records. Filters apply to those returned records; this is not a complete historical export.</p><form className="filter-bar" method="GET"><label>Event<select name="event" defaultValue={event}><option value="">All events</option>{Array.from(new Set(logs.map(log => log.event_name))).map(name => <option key={name}>{name}</option>)}</select></label><label>From (UTC)<input type="date" name="from" defaultValue={from} /></label><label>To (UTC)<input type="date" name="to" defaultValue={to} /></label><button type="submit">Apply filters</button><Link href="/audit">Clear</Link></form>{!logsResult.available ? <ApiNotice result={logsResult} label="Audit records unavailable" /> : filtered.length ? <><div className="audit-list">{paged.map(log => <article className="audit-row" key={log.id}><div><strong>{log.event_name.replaceAll("_", " ")}</strong><span>{new Date(log.timestamp).toLocaleString()}</span><details><summary>View recorded payload</summary><pre>{log.payload}</pre></details></div></article>)}</div><div className="table-footer"><span>{`Showing ${(current - 1) * PAGE_SIZE + 1}–${Math.min(current * PAGE_SIZE, filtered.length)} of ${filtered.length}`}</span><nav className="table-pagination" aria-label="Audit records pagination">{current > 1 ? <Link href={pageHref(current - 1)}>Previous</Link> : <span aria-disabled="true">Previous</span>}<span aria-live="polite">Page {current} of {totalPages}</span>{current < totalPages ? <Link href={pageHref(current + 1)}>Next</Link> : <span aria-disabled="true">Next</span>}</nav></div></> : <p className="empty-state">No audit records match these filters.</p>}</section></main></AppShell>;
}

