"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PageLoading } from "./page-loading";

export function LogoutButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function logout() {
    setBusy(true);
    try {
      await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
    } finally {
      window.localStorage.removeItem("maintainnexus_token");
      router.replace("/login?logged_out=1");
      router.refresh();
    }
  }

  return <>{busy && <PageLoading />}<button className="logout-button" disabled={busy} onClick={logout} type="button">{busy ? "Signing out..." : "Sign out"}</button></>;
}
