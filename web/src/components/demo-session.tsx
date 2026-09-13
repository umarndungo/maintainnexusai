"use client";

import { useEffect, useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function DemoSession() {
  const [signedIn, setSignedIn] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSignedIn(Boolean(window.localStorage.getItem("maintainnexus_token")));
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  async function signIn() {
    setBusy(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/auth/login`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email: "engineer@maintainnexus.ai", password: "engineer-demo" }),
      });
      if (!response.ok) throw new Error("Login failed");
      const result = await response.json();
      window.localStorage.setItem("maintainnexus_token", result.access_token);
      setSignedIn(true);
    } finally {
      setBusy(false);
    }
  }

  function signOut() {
    window.localStorage.removeItem("maintainnexus_token");
    setSignedIn(false);
  }

  return signedIn ? <button className="session-button signed-in" onClick={signOut} type="button">Engineer session</button> : <button className="session-button" disabled={busy} onClick={signIn} type="button">{busy ? "Connecting..." : "Start demo session"}</button>;
}
