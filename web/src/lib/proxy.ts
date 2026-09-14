import "server-only";
import { NextRequest, NextResponse } from "next/server";
import { apiOrigin, getCurrentUser, type UserRole } from "./api";

export const apiBaseUrl = apiOrigin;

export async function authorize(request: NextRequest, roles: UserRole[]) {
  const token = request.cookies.get("maintainnexus_token")?.value;
  if (!token) return { error: NextResponse.json({ detail: "Sign in first" }, { status: 401 }) };
  const result = await getCurrentUser(token);
  if (!result.available || !result.data) return { error: NextResponse.json({ detail: "Session validation failed" }, { status: result.status === 401 ? 401 : 503 }) };
  if (!roles.includes(result.data.role)) return { error: NextResponse.json({ detail: "This role cannot perform this action" }, { status: 403 }) };
  return { token };
}

// Keep business logic in FastAPI; web routes only attach the cookie token.
export async function proxy(request: NextRequest, path: string, roles: UserRole[]) {
  const session = await authorize(request, roles);
  if (session.error) return session.error;
  try {
    const response = await fetch(`${apiBaseUrl()}${path}`, {
      method: request.method,
      headers: { "content-type": "application/json", authorization: `Bearer ${session.token}` },
      body: request.method === "GET" ? undefined : await request.text(),
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
    return new NextResponse(await response.text(), { status: response.status, headers: { "content-type": response.headers.get("content-type") ?? "application/json", "cache-control": "no-store" } });
  } catch {
    return NextResponse.json({ detail: "The MaintainNexus API is unavailable" }, { status: 503 });
  }
}
