import "server-only";
import { workspacePath } from "./workspace";
import { cache } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getCurrentUser, type UserRole } from "./api";
export const getRequestTimestamp = cache(async () => Date.now());

export const getSession = cache(async () => {
  const token = (await cookies()).get("maintainnexus_token")?.value;
  if (!token) return null;
  const result = await getCurrentUser(token);
  if (result.status === 401) return null;
  if (!result.available || !result.data) redirect("/session-unavailable");
  return { token, user: result.data };
});

export async function requireSession(roles: UserRole[]) {
  const session = await getSession();
  if (!session) redirect("/login?expired=1");
  if (!roles.includes(session.user.role)) {
    redirect(workspacePath(session.user.role));
  }
  return session;
}
