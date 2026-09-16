import { AppShell } from "@/components/app-shell";
import { requireSession } from "@/lib/session";
import Link from "next/link";

export default async function ProfilePage() {
  const { user } = await requireSession(["engineer", "supervisor", "executive", "technician"]);
  return (
    <AppShell user={user}>
      <header className="detail-header"><div><h1>My profile</h1><p>Your account details and assigned stations.</p></div></header>
      <section className="panel profile-details" aria-label="Profile details">
        <dl>
          <div><dt>Name</dt><dd>{user.name ?? "Not supplied"}</dd></div>
          <div><dt>Account ID</dt><dd>{user.id}</dd></div>
          <div><dt>Role</dt><dd>{user.role}</dd></div>
          <div><dt>Assigned stations</dt><dd>{user.station_ids.length ? user.station_ids.join(", ") : "No station assignments listed"}</dd></div>
        </dl>
      </section>
      <p><Link href="/change-password">Change password</Link></p>
    </AppShell>
  );
}
