"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { CurrentUser } from "@/lib/api";
import { LogoutButton } from "./logout-button";

export function ProfileMenu({ user, initials }: { user: CurrentUser; initials: string }) {
  const [open, setOpen] = useState(false);
  const container = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    function dismiss(event: PointerEvent) {
      if (!container.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, [open]);

  return (
    <div className="profile-menu" ref={container}
      onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}
      onKeyDown={event => {
        if (event.key === "Escape" && open) {
          setOpen(false);
          trigger.current?.focus();
        }
      }}>
      <button className="profile-trigger" type="button" ref={trigger}
        aria-label={`Account options for ${user.name ?? user.id}`}
        aria-expanded={open} aria-controls="profile-options" onClick={() => setOpen(!open)}>
        <span className="user-avatar">{initials}</span>
        <span className="topbar-user"><strong>{user.name ?? user.id}</strong><small>{user.role}</small></span>
        <span aria-hidden="true">▾</span>
      </button>
      {open && <div className="profile-options" id="profile-options">
        <Link href="/profile" onClick={() => setOpen(false)}>View profile</Link>
        <LogoutButton />
      </div>}
    </div>
  );
}
