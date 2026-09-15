import { workspacePath } from "@/lib/workspace";
import { ApiNotice } from "@/components/api-notice";
import Link from "@/components/navigation-link";
import { requireSession } from "@/lib/session";
import { getAuditLogs, getAuditVerification } from "@/lib/api";
import { AppShell } from "@/components/app-shell";


export default async function AuditPage({ searchParams }: { searchParams: Promise<{ event?: string; from?: string; to?: string }> }) {
  const { token, user } = await requireSession(["engineer", "supervisor", "executive"]);
  const { event = "", from = "", to = "" } = await searchParams;
  const [result, logsResult] = await Promise.all([getAuditVerification(token), getAuditLogs(token)]);
  const verification = result.data;
  const logs = logsResult.data ?? [];
  const start = from ? Date.parse(`${from}T00:00:00Z`) : -Infinity;
  const end = to ? Date.parse(`${to}T23:59:59.999Z`) : Infinity;
  const filtered = logs.filter(log => (!event || log.event_name === event) && Date.parse(log.timestamp) >= start && Date.parse(log.timestamp) <= end);
  const state = !verification ? "unavailable" : verification.chain_integrity ? "valid" : "invalid";
  return <AppShell user={user}><main className="detail-shell"><header className="detail-header"><div><span className="eyebrow">TRACEABILITY / INTEGRITY</span><h1>Audit chain</h1><p>Read-only records and the backend verification result.</p></div><div className="detail-actions"><Link href={workspacePath(user.role)}>Back to workspace</Link></div></header><section className={`integrity-hero integrity-${state}`}><span className="integrity-symbol">{state === "valid" ? "?" : state === "invalid" ? "!" : "?"}</span><div><span className="eyebrow">{verification?.chain ?? "Audit chain"}</span><h2>{state === "valid" ? "Chain verified" : state === "invalid" ? "Verification failed" : "Verification unavailable"}</h2><p>{verification ? `${verification.checked_events} events checked at ${new Date(verification.verified_at).toLocaleString()}.` : "The backend has not returned a verification result. This does not establish that the chain passed or failed."}</p></div></section><ApiNotice result={result} label="Audit verification unavailable" /><section className="detail-panel"><h2>Audit records</h2><p className="monitoring-context">This endpoint returns the latest 50 backend audit records. Filters apply to those returned records; this is not a complete historical export.</p><form className="filter-bar" method="GET"><label>Event<select name="event" defaultValue={event}><option value="">All events</option>{Array.from(new Set(logs.map(log => log.event_name))).map(name => <option key={name}>{name}</option>)}</select></label><label>From (UTC)<input type="date" name="from" defaultValue={from} /></label><label>To (UTC)<input type="date" name="to" defaultValue={to} /></label><button type="submit">Apply filters</button><Link href="/audit">Clear</Link></form>{!logsResult.available ? <ApiNotice result={logsResult} label="Audit records unavailable" /> : filtered.length ? <div className="audit-list">{filtered.map(log => <article className="audit-row" key={log.id}><div><strong>{log.event_name.replaceAll("_", " ")}</strong><span>{new Date(log.timestamp).toLocaleString()}</span><details><summary>View recorded payload</summary><pre>{log.payload}</pre></details></div></article>)}</div> : <p className="empty-state">No audit records match these filters.</p>}</section></main></AppShell>;
}

