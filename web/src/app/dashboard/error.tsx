"use client";

export default function DashboardError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main className="route-error"><span className="eyebrow">THE WATCH PAUSED</span><h1>We could not gather the latest station story.</h1><p>The backend may be restarting or the connection may have gone quiet.</p><button className="login-submit" onClick={() => reset()} type="button">Try again <span>-&gt;</span></button></main>;
}
