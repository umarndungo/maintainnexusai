"use client";

import Link, { useLinkStatus } from "next/link";
import type { ComponentProps } from "react";
import { createPortal } from "react-dom";
import { PageLoading } from "./page-loading";

function PendingNavigation() {
  const { pending } = useLinkStatus();
  return pending ? createPortal(<PageLoading />, document.body) : null;
}

export default function NavigationLink({ children, ...props }: ComponentProps<typeof Link>) {
  return <Link {...props}>{children}<PendingNavigation /></Link>;
}
