import { NextRequest, NextResponse } from "next/server";

const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";

export async function POST(request: NextRequest) {
  const response = await fetch(`${apiBaseUrl}/api/v1/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: await request.text(),
  });

  const body = await response.text();
  if (!response.ok) {
    return new NextResponse(body, {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  }

  const result = JSON.parse(body) as { access_token: string };
  const nextResponse = NextResponse.json(result);
  nextResponse.cookies.set("maintainnexus_token", result.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 8,
  });
  return nextResponse;
}
