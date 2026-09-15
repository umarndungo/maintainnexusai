import { NextRequest, NextResponse } from "next/server";
import { apiBaseUrl } from "@/lib/proxy";
import { getCurrentUser } from "@/lib/api";

export async function POST(request: NextRequest) {
  try {
    const credentials = await request.json().catch(() => null);
    if (!credentials || typeof credentials.user_id !== "string") return NextResponse.json({ detail: "A user ID is required" }, { status: 400 });
    const response = await fetch(`${apiBaseUrl()}/api/v1/auth/login`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ user_id: credentials.user_id }), cache: "no-store", signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) return NextResponse.json({ detail: "Sign-in was rejected by the API" }, { status: response.status });
    const result = await response.json() as { access_token?: string; expires_in?: number };
    if (!result.access_token) return NextResponse.json({ detail: "The API returned no session token" }, { status: 502 });
    const identity = await getCurrentUser(result.access_token);
    if (!identity.available || !identity.data) return NextResponse.json({ detail: "The API could not confirm your identity" }, { status: 503 });
    // Do not send the bearer token to browser JavaScript.
    const nextResponse = NextResponse.json({ user: identity.data });
    const lifetime = Number.isInteger(result.expires_in) && result.expires_in! > 0 ? Math.min(result.expires_in!, 28800) : 3600;
    nextResponse.cookies.set("maintainnexus_token", result.access_token, { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", path: "/", maxAge: lifetime });
    return nextResponse;
  } catch {
    return NextResponse.json({ detail: "The MaintainNexus AI API is unavailable" }, { status: 503 });
  }
}
