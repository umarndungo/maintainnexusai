"use client";

import { useEffect, useState } from "react";

export function SessionRenewal() {
  const [, setMessage] = useState("");
  useEffect(() => {
    let busy = false;
    let stopped = false;
    const controller = new AbortController();
    async function renew() {
      if (busy || stopped || document.visibilityState !== "visible") return;
      busy = true;
      try {
        const response = await fetch("/api/auth/refresh", { method: "POST", signal: controller.signal });
        if (stopped) return;
        if (response.status === 401) {
          setMessage("Your session has expired. Sign in again to continue.");
        } else if (!response.ok) {
          setMessage("Session renewal is temporarily unavailable. Retrying automatically.");
        } else setMessage("");
      } catch {
        if (!stopped) setMessage("Connection interrupted. Session renewal will retry automatically.");
      } finally { busy = false; }
    }
    void renew();
    const timer = setInterval(renew, 5 * 60 * 1000);
    const stop = () => { stopped = true; controller.abort(); clearInterval(timer); };
    window.addEventListener("session-signout", stop);
    document.addEventListener("visibilitychange", renew);
    window.addEventListener("online", renew);
    return () => { stop(); window.removeEventListener("session-signout", stop); document.removeEventListener("visibilitychange", renew); window.removeEventListener("online", renew); };
  }, []);
  return null;
}
