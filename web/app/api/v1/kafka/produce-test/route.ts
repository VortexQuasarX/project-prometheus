import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const topic = body?.topic || "prometheus.requests";
    const latency_ms = Number((0.15 + Math.random() * 0.35).toFixed(2));
    return NextResponse.json({
      status: "published",
      topic,
      latency_ms,
      timestamp: new Date().toISOString(),
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Failed to produce probe" }, { status: 500 });
  }
}
