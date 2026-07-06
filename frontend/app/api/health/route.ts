import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json({
    status: "ok",
    version: "1.0.0-vercel-demo",
    demo_mode: true,
    supabase: false,
  });
}
