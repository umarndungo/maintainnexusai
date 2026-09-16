import { NextRequest, NextResponse } from "next/server";
import { apiBaseUrl } from "@/lib/proxy";
import { cookies } from "next/headers";

export async function PATCH(request: NextRequest) {
  const token = (await cookies()).get("maintainnexus_token")?.value;
  if (!token) return NextResponse.json({ detail: "Sign-in required" }, { status: 401 });
  try {
    const body = await request.json().catch(() => null);
    const response = await fetch(`${apiBaseUrl()}/api/v1/auth/change-password`, {
      method: "PATCH",
      headers: { "content-type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
    const result = await response.json().catch(() => ({ detail: "Password change failed" }));
    if (!response.ok) return NextResponse.json(result, { status: response.status });
    const nextResponse = NextResponse.json(result);
    nextResponse.cookies.delete("maintainnexus_must_change_password");
    return nextResponse;
  } catch {
    return NextResponse.json({ detail: "The MaintainNexus AI API is unavailable" }, { status: 503 });
  }
}