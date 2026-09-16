"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

export function ChangePasswordForm() {
  const router = useRouter();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmation) {
      setError("New passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const response = await fetch("/api/auth/change-password", {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Password change failed.");
      router.replace("/profile");
      router.refresh();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Password change failed.");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} aria-busy={busy}>
      <label htmlFor="current-password">Current password</label>
      <input id="current-password" type="password" value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} required disabled={busy} />
      <label htmlFor="new-password">New password</label>
      <input id="new-password" type="password" value={newPassword} onChange={event => setNewPassword(event.target.value)} minLength={8} required disabled={busy} />
      <label htmlFor="confirm-password">Confirm new password</label>
      <input id="confirm-password" type="password" value={confirmation} onChange={event => setConfirmation(event.target.value)} minLength={8} required disabled={busy} />
      {error && <p className="operation-error" role="alert">{error}</p>}
      <button type="submit" disabled={busy}>{busy ? "Updating..." : "Update password"}</button>
    </form>
  );
}