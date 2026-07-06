import { NextResponse } from "next/server";
import { demoConfigs } from "@/lib/demo";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ datasetId: string }> },
) {
  const { datasetId } = await context.params;
  try {
    return NextResponse.json({ configs: demoConfigs(datasetId) });
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Dataset not found" },
      { status: 404 },
    );
  }
}
