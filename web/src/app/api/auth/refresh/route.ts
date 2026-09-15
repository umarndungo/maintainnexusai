import { NextRequest, NextResponse } from "next/server";
import { apiOrigin } from "@/lib/api";

export async function POST(request: NextRequest) {
  const token = request.cookies.get("maintainnexus_token")?.value;
  if (!token) return NextResponse.json({ detail: "Sign in again" }, { status: 401 });
  try {
    const response = await fetch(`${apiOrigin()}/api/v1/auth/refresh`, {
      method: "POST", headers: { authorization: `Bearer ${token}` },
      cache: "no-store", signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) return NextResponse.json({ detail: "Session renewal unavailable" }, { status: response.status });
    const data = await response.json();
    if (typeof data.access_token !== "string" || !Number.isInteger(data.expires_in) || data.expires_in <= 0 || data.expires_in > 28800) {
      return NextResponse.json({ detail: "Invalid renewal response" }, { status: 502 });
    }
    const result = NextResponse.json({ renewed: true }, { headers: { "cache-control": "no-store" } });
    result.cookies.set("maintainnexus_token", data.access_token, { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", path: "/", maxAge: data.expires_in });
    return result;
  } catch {
    return NextResponse.json({ detail: "Session service temporarily unavailable" }, { status: 503 });
  }
}
