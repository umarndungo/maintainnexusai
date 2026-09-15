"use client";
import { useState, useSyncExternalStore, type ReactNode } from "react";
import { workspacePath, workspaceTitle } from "@/lib/workspace";
import { usePathname } from "next/navigation";
import Link from "./navigation-link";
import { LiveUpdates } from "./live-updates";
import { ProfileMenu } from "./profile-menu";
import { Brand, Icon, type IconName } from "./ui";
import type { CurrentUser } from "@/lib/api";
function subscribeViewport(callback: () => void) {
  const media = window.matchMedia("(max-width: 767px)");
  media.addEventListener("change", callback);
  return () => media.removeEventListener("change", callback);
}
export function AppShell({
  user,
  children,
}: {
  user: CurrentUser;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const isMobile = useSyncExternalStore(
    subscribeViewport,
    () => window.matchMedia("(max-width: 767px)").matches,
    () => false,
  );
  const readOnly = user.role === "executive";
  const links: Array<{ href: string; label: string; icon: IconName }> = [
    {
      href: workspacePath(user.role),
      label: workspaceTitle(user.role),
      icon: "dashboard",
    },
    { href: "/monitoring", label: "Live Monitoring", icon: "monitoring" },
    ...(!readOnly
      ? [
          {
            href: "/work-orders",
            label: "Work Orders",
            icon: "orders" as const,
          },
        ]
      : []),
    { href: "/equipment", label: "Equipment", icon: "equipment" },
    { href: "/alerts", label: "Alerts", icon: "alerts" },
    ...(!readOnly
      ? [{ href: "/approvals", label: "Approvals", icon: "approvals" as const }]
      : []),
    ...(user.role === "supervisor" || readOnly
      ? [{ href: "/reports", label: "Reports", icon: "reports" as const }]
      : []),
    { href: "/audit", label: "Audit Log", icon: "audit" },
  ];
  if (user.role === "supervisor") {
    const priority = ["/supervisor", "/approvals", "/work-orders", "/equipment", "/monitoring", "/alerts", "/reports", "/audit"];
    links.sort((a, b) => priority.indexOf(a.href) - priority.indexOf(b.href));
  }
  if (readOnly) {
    const priority = ["/executive", "/reports", "/equipment", "/monitoring", "/alerts", "/audit"];
    links.sort((a, b) => priority.indexOf(a.href) - priority.indexOf(b.href));
  }
  const initials = (user.name ?? user.id)
    .split(/[ -]/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
  return (
    <div
      className={`workspace-shell role-${user.role} ${pathname === "/reports" ? "reports-shell" : ""} ${collapsed ? "nav-collapsed" : ""} ${mobileOpen ? "mobile-nav-open" : ""}`}
    >
      <a className="skip-link" href="#main-workspace">
        Skip to content
      </a>
      <aside className="app-sidebar" id="app-navigation">
        <Link
          className="sidebar-brand"
          href={workspacePath(user.role)}
        >
          <Brand company={pathname === "/reports"} />
        </Link>
        <button
          className="icon-button mobile-nav-close"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
          type="button"
        >
          ×
        </button>
        <nav aria-label="Main navigation" onClick={() => setMobileOpen(false)}>
          {links.map((link) => (
            <Link
              key={link.href}
              className={`sidebar-link ${pathname === link.href || pathname.startsWith(`${link.href}/`) ? "active" : ""}`}
              href={link.href}
              aria-current={pathname === link.href ? "page" : undefined}
              title={link.label}
            >
              <Icon name={link.icon} />
              <span>{link.label}</span>
            </Link>
          ))}
        </nav>
        <div className="sidebar-scene">
          <p>
            Reliable Assets.
            <br />A Stronger Kenya.
          </p>
          <i />
        </div>
        <footer className="app-sidebar-footer">
          <div className="sidebar-user">
            <span className="user-avatar">{initials}</span>
            <div>
              <strong>{user.name ?? user.id}</strong>
              <small>
                {user.role} ·{" "}
                {user.station_ids.join(", ") || "Network scope"}
              </small>
            </div>
          </div>
        </footer>
      </aside>
      <div className="workspace-main">
        <header className="app-topbar">
          <button
            className="icon-button"
            type="button"
            title={collapsed ? "Expand navigation" : "Collapse navigation"}
            aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
            aria-controls="app-navigation"
            aria-expanded={isMobile ? mobileOpen : !collapsed}
            onClick={() =>
              isMobile ? setMobileOpen(!mobileOpen) : setCollapsed(!collapsed)
            }
          >
            <Icon name="menu" />
          </button>
          <div className="scope-label">
            <Icon name="equipment" />
            <span>{user.station_ids.join(", ") || "Network operations"}</span>
          </div>
          <div className="app-topbar-right">
            <LiveUpdates />
            <ProfileMenu user={user} initials={initials} />
          </div>
        </header>
        <div id="main-workspace" className="workspace-content">
          {children}
        </div>
      </div>
    </div>
  );
}
