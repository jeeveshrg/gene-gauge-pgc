import { NextResponse } from "next/server";
import { demoMarkdownReport, runDemoAnalysis } from "@/lib/demo";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  try {
    const result = runDemoAnalysis(id);
    return new NextResponse(demoMarkdownReport(result), {
      headers: {
        "content-type": "text/markdown; charset=utf-8",
        "content-disposition": `inline; filename="genegauge-${id.slice(0, 16)}.md"`,
      },
    });
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Analysis not found" },
      { status: 404 },
    );
  }
}
