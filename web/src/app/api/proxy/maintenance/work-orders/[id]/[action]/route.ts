import { NextRequest, NextResponse } from "next/server";

const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";
const allowedActions = new Set(["approve", "reject", "escalate"]);

type RouteContext = { params: Promise<{ id: string; action: string }> };

export async function PATCH(request: NextRequest, context: RouteContext) {
  const { id, action } = await context.params;
  if (!allowedActions.has(action)) {
    return NextResponse.json({ detail: "Unsupported work-order action" }, { status: 400 });
  }

  const authorization = request.headers.get("authorization");
  const response = await fetch(`${apiBaseUrl}/api/v1/maintenance/work-orders/${encodeURIComponent(id)}/${action}`, {
    method: "PATCH",
    headers: authorization ? { authorization } : { authorization: `Bearer ${request.cookies.get("maintainnexus_token")?.value ?? ""}` },
  });

  const body = await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
  });
}
