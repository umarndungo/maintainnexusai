import Image from "next/image";
import type { ReactNode } from "react";
const paths = {
  dashboard: "M3 10l9-7 9 7M5 9v12h5v-7h4v7h5V9",
  monitoring: "M3 12h4l3-7 4 14 3-7h4",
  orders: "M8 4H5v17h14V4h-3M8 3h8v4H8zM8 12h8M8 16h6",
  equipment: "M4 7h16v14H4zM8 7V3h8v4M8 11h2M14 11h2M8 16h2M14 16h2",
  alerts: "M6 9a6 6 0 0112 0v5l2 3H4l2-3zM10 21h4",
  approvals: "M4 4h16v16H4zM8 12l3 3 6-7",
  reports: "M4 3v18h17M8 17v-5M13 17V7M18 17V4",
  audit: "M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6",
  menu: "M4 6h16M4 12h16M4 18h16",
  arrow: "M4 12h16M14 6l6 6-6 6",
  clock: "M12 8v5l3 2M21 12a9 9 0 11-18 0 9 9 0 0118 0",
  search: "M21 21l-6-6M17 10a7 7 0 11-14 0 7 7 0 0114 0",
  user: "M20 21v-3a8 5 0 00-16 0v3M16 7a4 4 0 11-8 0 4 4 0 018 0",
} as const;
export type IconName = keyof typeof paths;
export function Icon({
  name,
  className = "",
}: {
  name: IconName;
  className?: string;
}) {
  return (
    <svg
      className={`ui-icon ${className}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  );
}
export function Brand({ company = false }: { company?: boolean }) {
  return (
    <div className={`product-brand ${company ? "company-brand" : ""}`}>
      <Image src="/brand/kpc-mark.svg" width={40} height={56} alt="KPC" />
      <div>
        <strong>
          {company ? (
            "Kenya Pipeline Company"
          ) : (
            <>
              MaintainNexus <em>AI</em>
            </>
          )}
        </strong>
        <small>
          {company ? "Energy for a Better Kenya" : "ASSETS · PEOPLE · UPTIME"}
        </small>
      </div>
    </div>
  );
}
export function StatCard({
  label,
  value,
  detail,
  icon = "equipment",
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  detail: string;
  icon?: IconName;
  tone?: string;
}) {
  return (
    <article className={`stat-card tone-${tone}`}>
      <span className="stat-icon">
        <Icon name={icon} />
      </span>
      <div>
        <h3>{label}</h3>
        <strong>{value}</strong>
        <p>{detail}</p>
      </div>
    </article>
  );
}
export function PageHeader({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children && <div className="page-header-actions">{children}</div>}
    </header>
  );
}
export function StatusBadge({ status }: { status?: string }) {
  const value = status ?? "UNKNOWN";
  return (
    <span className={`status-badge badge-${value.toLowerCase()}`}>
      <span aria-hidden="true">●</span>
      {value.replaceAll("_", " ").toLowerCase()}
    </span>
  );
}
