"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

type Role = "engineer" | "supervisor" | "executive";
const accounts: Record<Role, { label: string; detail: string; userId: string }> = {
  engineer: { label: "Engineer", detail: "Review signals and approve work", userId: "engineer-demo" },
  supervisor: { label: "Supervisor", detail: "Resolve escalations across stations", userId: "supervisor-demo" },
  executive: { label: "Executive", detail: "See the value across the network", userId: "executive-demo" },
};
const roleVisuals: Record<Role, { eyebrow: string; title: string; detail: string; metric: string; metricLabel: string; bars: number[]; status: string }> = {
  engineer: { eyebrow: "THE DEPOT, RIGHT NOW", title: "Small signals. Earlier action.", detail: "A rising vibration becomes a clear next step before the shift turns difficult.", metric: "0.87", metricLabel: "risk understood", bars: [28, 43, 35, 62, 78], status: "SIGNAL RECEIVED" },
  supervisor: { eyebrow: "THE DEPOT, TOGETHER", title: "Nothing important falls between shifts.", detail: "Escalations gather in one place, ready for the person who can move them forward.", metric: "03", metricLabel: "items needing care", bars: [45, 36, 55, 48, 70], status: "QUEUE IN MOTION" },
  executive: { eyebrow: "THE NETWORK, AT A GLANCE", title: "A clearer day, measured over time.", detail: "Reliability becomes a story you can see: less interruption, more confidence, more room to grow.", metric: "99.9%", metricLabel: "system readiness", bars: [44, 52, 58, 66, 82], status: "VALUE IN VIEW" },
};

export default function LoginPage() {
  const router = useRouter();
  const [role, setRole] = useState<Role>("engineer");
  const [userId, setUserId] = useState(accounts.engineer.userId);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function selectRole(nextRole: Role) {
    setRole(nextRole);
    setUserId(accounts[nextRole].userId);
    setError("");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/auth/login", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ user_id: userId }) });
      if (!response.ok) { const result = await response.json().catch(() => ({ detail: "Login failed" })); throw new Error(result.detail ?? "Login failed"); }
      const result = await response.json() as { user?: { role?: Role } };
      const authenticatedRole = result.user?.role ?? role;
      router.replace(authenticatedRole === "executive" ? "/executive" : "/dashboard");
      router.refresh();
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Login failed");
    } finally { setBusy(false); }
  }

  const visual = roleVisuals[role];
  return <main className={`login-shell role-${role}`}><section className="login-panel"><div className="brand login-brand"><span className="brand-mark">M</span><span>MAINTAIN<span className="brand-accent">NEXUS</span></span></div><div className="login-heading"><span className="eyebrow">YOUR NEXT SHIFT, MADE CLEARER</span><h1>Welcome to the watch.</h1><p>See the small thing while it is still small. Choose a workspace to begin.</p></div><div className="role-switcher" role="tablist" aria-label="Choose workspace">{(Object.keys(accounts) as Role[]).map((item) => <button className={role === item ? "role-option selected" : "role-option"} key={item} onClick={() => selectRole(item)} role="tab" type="button"><strong>{accounts[item].label}</strong><span>{accounts[item].detail}</span></button>)}</div><form onSubmit={submit}><label>User ID<input autoComplete="username" onChange={(event) => setUserId(event.target.value)} value={userId} required /></label>{error && <div className="login-error">{error}</div>}<button className="login-submit" disabled={busy} type="submit">{busy ? "Opening..." : `Open ${accounts[role].label.toLowerCase()} workspace`}<span>-&gt;</span></button></form><div className="login-note"><span className="note-check">✓</span><span><strong>Demo access is ready</strong><small>Demo user IDs are prefilled. Sign-in uses the backend; password authentication is not available yet.</small></span></div></section><aside className="login-aside"><div className="aside-top"><span className="eyebrow">MAINTAINNEXUS / 01</span><span className="aside-status"><i />Systems watching</span></div><div className="aside-message"><span className="eyebrow">{visual.eyebrow}</span><strong>{visual.title}</strong><p>{visual.detail}</p></div><div className="signal-card"><div><span>{visual.status}</span><b>{visual.metric}</b></div><div className="signal-line">{visual.bars.map((height) => <i key={height} style={{ height: `${height}%` }} />)}</div><div className="signal-caption"><span>{visual.metricLabel}</span><strong>{role === "engineer" ? "People have time" : role === "supervisor" ? "The right work, visible" : "More room to grow"}</strong></div></div><div className="aside-footer"><span>{role === "engineer" ? "Notice" : role === "supervisor" ? "Resolve" : "See clearly"}</span><i /><span>{role === "engineer" ? "Understand" : role === "supervisor" ? "Coordinate" : "Compare"}</span><i /><span>{role === "engineer" ? "Act" : role === "supervisor" ? "Move forward" : "Lead"}</span></div></aside></main>;
}
