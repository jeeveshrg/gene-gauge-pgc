import { NextResponse } from "next/server";
import { runDemoAnalysis } from "@/lib/demo";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  try {
    return NextResponse.json(runDemoAnalysis(id));
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Analysis not found" },
      { status: 404 },
    );
  }
}
