import Link from "next/link";
import { LogoutButton } from "@/components/logout-button";

export default function SessionUnavailablePage() {
  return <main className="detail-shell"><h1>Session service unavailable</h1><p>We could not confirm your role and station access. Reconnect to the API, then try again.</p><div className="detail-actions"><Link href="/dashboard">Try again</Link><LogoutButton /></div></main>;
}
