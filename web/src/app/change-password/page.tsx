import { ChangePasswordForm } from "@/components/change-password-form";
import { AppShell } from "@/components/app-shell";
import { requireSession } from "@/lib/session";

export default async function ChangePasswordPage() {
  const { user } = await requireSession(["engineer", "supervisor", "executive", "technician"]);
  return (
    <AppShell user={user}>
      <header className="detail-header">
        <div><h1>Change password</h1><p>Update the password for your MaintainNexus account.</p></div>
      </header>
      <section className="panel" aria-label="Change password form">
        <ChangePasswordForm />
      </section>
    </AppShell>
  );
}