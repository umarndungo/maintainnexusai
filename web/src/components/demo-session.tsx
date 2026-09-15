"use client";

import Link from "@/components/navigation-link";

// Preserve the legacy entry point while using the shared cookie-based login.
export function DemoSession() {
  return <Link className="session-button" href="/login">Start demo session</Link>;
}
