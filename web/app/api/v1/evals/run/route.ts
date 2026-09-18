import { NextRequest, NextResponse } from "next/server";
import { createNewEvalRun } from "@/lib/eval-store";

export async function POST(req: NextRequest) {
  try {
    const run = createNewEvalRun();
    return NextResponse.json({
      run_id: run.run_id,
      status: run.status,
      total_cases: run.total_cases,
      passed_cases: run.passed_cases,
      failed_cases: run.failed_cases,
      avg_metrics: run.avg_metrics,
      duration_ms: run.duration_ms,
      created_at: run.created_at,
    });
  } catch (err: any) {
    return NextResponse.json(
      { error: { code: "internal_error", message: err.message || "Failed to execute eval run" } },
      { status: 500 }
    );
  }
}
