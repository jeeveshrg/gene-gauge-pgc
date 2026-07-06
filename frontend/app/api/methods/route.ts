import { NextResponse } from "next/server";
import { demoMethods } from "@/lib/demo";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json(demoMethods());
}
