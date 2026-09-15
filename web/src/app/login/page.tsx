"use client";
import { workspacePath } from "@/lib/workspace";
import Image from "next/image";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Brand, Icon } from "@/components/ui";
export default function LoginPage() {
  const router = useRouter();
  const [userId, setUserId] = useState("engineer-demo");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
      const result = await response.json();
      if (!response.ok)
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "Sign-in failed. Check your account ID and try again.",
        );
      router.replace(
        workspacePath(result.user.role),
      );
      router.refresh();
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Sign-in unavailable. Try again.",
      );
      setBusy(false);
    }
  }
  return (
    <main className="auth-shell">
      <section className="auth-visual">
        <Image
          src="/images/auth-industrial.jpg"
          alt="Petroleum storage tanks and industrial pipeline infrastructure"
          fill
          sizes="(max-width: 767px) 100vw, 50vw"
          priority
        />
        <div className="auth-overlay" />
        <div className="auth-brand">
          <Brand />
        </div>
        <div className="auth-story">
          <h2>Powering Kenya’s Progress Through Reliable Assets</h2>
          <i className="brand-rule" />
          <p>
            Monitor, maintain and optimise critical assets for a safer, more
            efficient and resilient energy future.
          </p>
          <div className="auth-values">
            <span>
              <Icon name="audit" />
              Safer
              <br />
              Operations
            </span>
            <span>
              <Icon name="reports" />
              Higher
              <br />
              Availability
            </span>
            <span>
              <Icon name="monitoring" />
              Continuous
              <br />
              Monitoring
            </span>
          </div>
        </div>
        <small className="auth-copyright">
          MaintainNexus AI · Assets. People. Uptime.
        </small>
      </section>
      <section className="auth-form-side">
        <div className="auth-company">
          <Brand company />
        </div>
        <div className="auth-form-wrap">
          <i className="brand-rule" />
          <p className="auth-welcome">Welcome to</p>
          <h1>
              MaintainNexus <em>AI</em>
          </h1>
          <p className="auth-subtitle">
            Sign in to access your operational workspace.
          </p>
          <form onSubmit={submit} aria-busy={busy}>
            <label htmlFor="employee-id">Employee / demo account ID</label>
            <div className="auth-input">
              <Icon name="user" />
              <input
                id="employee-id"
                name="user_id"
                value={userId}
                onChange={(event) => setUserId(event.target.value)}
                autoComplete="username"
                required
                disabled={busy}
                aria-describedby="account-help"
              />
            </div>
            {error && (
              <p className="operation-error" role="alert">
                {error}
              </p>
            )}
            <button className="auth-submit" disabled={busy} type="submit">
              {busy ? "Signing in…" : "Sign in"}
              <Icon name="arrow" />
            </button>
          </form>
          <div className="auth-access-note" id="account-help">
            <Icon name="audit" />
            <div>
              <strong>Demo access</strong>
              <p>
                Use engineer-demo, supervisor-demo, or executive-demo. Your
                account determines your role and station access. Password and
                corporate SSO sign-in are not available.
              </p>
            </div>
          </div>
          <div className="auth-help">
            <strong>Need help?</strong>
            <p>Contact your system administrator for account access.</p>
          </div>
        </div>
      </section>
    </main>
  );
}
