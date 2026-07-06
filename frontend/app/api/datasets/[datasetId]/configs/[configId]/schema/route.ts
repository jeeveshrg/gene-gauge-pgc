import { NextResponse } from "next/server";
import { demoSchema } from "@/lib/demo";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ datasetId: string; configId: string }> },
) {
  const { datasetId, configId } = await context.params;
  try {
    return NextResponse.json(demoSchema(datasetId, configId));
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Schema not found" },
      { status: 404 },
    );
  }
}
