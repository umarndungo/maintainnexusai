"use client";

import { useState } from "react";
import { PageLoading } from "./page-loading";

export function LogoutButton() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function logout() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "same-origin",
        signal: AbortSignal.timeout(10000),
      });
      if (!response.ok) throw new Error("Sign-out failed");
      // Clear the client router cache and close live streams with a full navigation.
      window.location.replace("/login?logged_out=1");
    } catch {
      setError("Could not sign out. Please try again.");
      setBusy(false);
    }
  }

  return <>{busy && <PageLoading />}<button className="logout-button" disabled={busy} onClick={logout} type="button">{busy ? "Signing out..." : "Sign out"}</button>{error && <span role="alert">{error}</span>}</>;
}
