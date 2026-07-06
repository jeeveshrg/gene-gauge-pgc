import { NextResponse } from "next/server";
import { demoDatasets } from "@/lib/demo";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json({ datasets: demoDatasets(), demo_mode: true });
}
