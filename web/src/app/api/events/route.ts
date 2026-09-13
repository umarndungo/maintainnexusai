import { NextRequest, NextResponse } from "next/server";
import { apiBaseUrl, authorize } from "@/lib/proxy";

export async function GET(request: NextRequest) {
  const session = await authorize(request, ["engineer", "supervisor", "executive"]);
  if (session.error) return session.error;
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/events`, {
      headers: { authorization: `Bearer ${session.token}`, accept: "text/event-stream" },
      cache: "no-store", signal: request.signal,
    });
    if (!response.ok) return NextResponse.json({ detail: "Live events unavailable" }, { status: response.status });
    if (!response.headers.get("content-type")?.includes("text/event-stream")) return NextResponse.json({ detail: "Expected an SSE stream" }, { status: 502 });
    return new NextResponse(response.body, { headers: { "content-type": "text/event-stream", "cache-control": "no-cache, no-transform", "x-accel-buffering": "no" } });
  } catch {
    return NextResponse.json({ detail: "Live events unavailable" }, { status: 503 });
  }
}
