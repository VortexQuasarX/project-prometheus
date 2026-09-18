import { NextRequest, NextResponse } from "next/server";
import { getStoredEvalRuns } from "@/lib/eval-store";

export async function GET(req: NextRequest) {
  const runs = getStoredEvalRuns();
  const items = runs.map((r) => ({
    run_id: r.run_id,
    status: r.status,
    total_cases: r.total_cases,
    passed_cases: r.passed_cases,
    failed_cases: r.failed_cases,
    avg_metrics: r.avg_metrics,
    duration_ms: r.duration_ms,
    created_at: r.created_at,
  }));

  return NextResponse.json({
    items,
    total: items.length,
  });
}
