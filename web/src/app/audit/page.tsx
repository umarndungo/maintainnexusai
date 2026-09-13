import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getAuditVerification } from "@/lib/api";
import { LogoutButton } from "@/components/logout-button";

export default async function AuditPage() {
  const token = (await cookies()).get("maintainnexus_token")?.value;
  if (!token) redirect("/login");
  const result = await getAuditVerification(token);
  const verification = result.data;
  return <main className="detail-shell"><header className="detail-header"><div><span className="eyebrow">TRACEABILITY / INTEGRITY</span><h1>Audit chain</h1><p>A quiet proof that the record has not been quietly rewritten.</p></div><div className="detail-actions"><Link href="/dashboard">Back to station</Link><LogoutButton /></div></header><section className={`integrity-hero ${verification?.chain_integrity ? "integrity-valid" : "integrity-invalid"}`}><span className="integrity-symbol">{verification?.chain_integrity ? "✓" : "!"}</span><div><span className="eyebrow">{verification?.chain ?? "Audit chain"}</span><h2>{verification?.chain_integrity ? "Chain verified" : "Verification needs attention"}</h2><p>{verification ? `${verification.checked_events} events checked at ${new Date(verification.verified_at).toLocaleString()}.` : "The verification service did not return a result."}</p></div></section></main>;
}
