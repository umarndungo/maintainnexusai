import { NextResponse } from "next/server";

export async function POST() {
  const response = NextResponse.json({ signed_out: true });
  response.cookies.set("maintainnexus_token", "", {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
    expires: new Date(0),
  });
  return response;
}
