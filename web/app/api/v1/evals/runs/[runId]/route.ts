import { NextRequest, NextResponse } from "next/server";
import { getStoredEvalRuns } from "@/lib/eval-store";

export async function GET(
  req: NextRequest,
  { params }: { params: { runId: string } }
) {
  const { runId } = params;
  const runs = getStoredEvalRuns();
  const run = runs.find((r) => r.run_id === runId) || runs[0];

  if (!run) {
    return NextResponse.json({ error: "Run not found" }, { status: 404 });
  }

  return NextResponse.json({
    run_id: run.run_id,
    status: run.status,
    total_cases: run.total_cases,
    passed_cases: run.passed_cases,
    failed_cases: run.failed_cases,
    avg_metrics: run.avg_metrics,
    duration_ms: run.duration_ms,
    created_at: run.created_at,
    cases: run.cases,
  });
}
