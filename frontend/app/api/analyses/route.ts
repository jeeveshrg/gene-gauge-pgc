import { NextResponse } from "next/server";
import { createDemoAnalysisId, listDemoAnalyses } from "@/lib/demo";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json({ analyses: listDemoAnalyses() });
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    return NextResponse.json(
      { id: createDemoAnalysisId(body), status: "created" },
      { status: 201 },
    );
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Could not create analysis" },
      { status: 400 },
    );
  }
}
