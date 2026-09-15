import { NextRequest, NextResponse } from "next/server";
import { proxy } from "@/lib/proxy";

type Context = { params: Promise<{ id: string; action: string }> };

export async function PATCH(request: NextRequest, context: Context) {
  const { id, action } = await context.params;
  if (!["approve", "reject", "escalate", "assign", "start", "complete"].includes(action)) return NextResponse.json({ detail: "Unsupported action" }, { status: 400 });
  return proxy(request, `/api/v1/maintenance/work-orders/${encodeURIComponent(id)}/${action}`, action === "escalate" ? ["supervisor"] : ["engineer", "supervisor"]);
}

export async function GET(request: NextRequest, context: Context) {
  const { id, action } = await context.params;
  if (action !== "lifecycle") return NextResponse.json({ detail: "Unsupported resource" }, { status: 404 });
  return proxy(request, `/api/v1/maintenance/work-orders/${encodeURIComponent(id)}/lifecycle`, ["engineer", "supervisor", "executive"]);
}
