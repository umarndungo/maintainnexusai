import type { UserRole } from "./api";

export function workspacePath(role: UserRole) {
  return { engineer: "/dashboard", supervisor: "/supervisor", executive: "/executive", technician: "/access-denied" }[role];
}

export function workspaceTitle(role: UserRole) {
  return { engineer: "Station Operations", supervisor: "Maintenance Coordination", executive: "Network Outcomes", technician: "Mobile workspace" }[role];
}
