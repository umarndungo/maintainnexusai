import { NextRequest, NextResponse } from "next/server";
import { getCurrentUser } from "@/lib/api";

export async function GET(request: NextRequest) {
  const token = request.cookies.get("maintainnexus_token")?.value;
  const result = token ? await getCurrentUser(token) : null;
  return NextResponse.json({ available: !!result?.available }, {
    status: result?.available ? 200 : !token || result?.status === 401 ? 401 : 503,
    headers: { "cache-control": "no-store" },
  });
}
