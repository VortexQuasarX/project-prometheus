import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.SERVER_API_URL || "https://w6qubbix87.execute-api.ap-south-1.amazonaws.com";

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key",
    },
  });
}

export async function POST(req: Request) {
  try {
    const authHeader = req.headers.get("authorization") || "";
    let apiKey = req.headers.get("x-api-key") || "";
    if (!apiKey && authHeader.startsWith("Bearer ")) {
      apiKey = authHeader.replace("Bearer ", "").trim();
    }
    if (!apiKey) {
      apiKey = "prometheus-admin";
    }

    const body = await req.json();
    const messages = body.messages || [];
    const requestedModel = body.model || "mock-small";

    // Format messages for Prometheus pipeline
    let query = "";
    if (Array.isArray(messages) && messages.length > 0) {
      query = messages
        .map((m: { role?: string; content?: string }) => `${m.role ?? "user"}: ${m.content ?? ""}`)
        .join("\n");
    } else if (typeof body.query === "string") {
      query = body.query;
    } else {
      query = "Hello";
    }

    // Call Prometheus backend
    const backendRes = await fetch(`${BACKEND_URL}/api/v1/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify({
        query,
        model: requestedModel,
      }),
    });

    if (!backendRes.ok) {
      const errText = await backendRes.text();
      return NextResponse.json(
        {
          error: {
            message: `Prometheus backend error: ${errText}`,
            type: "backend_error",
            code: backendRes.status,
          },
        },
        { status: backendRes.status }
      );
    }

    const result = await backendRes.json();

    // Standard OpenAI chat completion format
    const completion = {
      id: result.request_id || `chatcmpl-${Date.now()}`,
      object: "chat.completion",
      created: Math.floor(Date.now() / 1000),
      model: result.model || requestedModel,
      choices: [
        {
          index: 0,
          message: {
            role: "assistant",
            content: result.answer || "",
          },
          finish_reason: "stop",
        },
      ],
      usage: {
        prompt_tokens: result.input_tokens || 0,
        completion_tokens: result.output_tokens || 0,
        total_tokens: (result.input_tokens || 0) + (result.output_tokens || 0),
      },
      prometheus_metadata: {
        latency_ms: result.latency_ms,
        cost_usd: result.estimated_cost_usd,
        cost_saved_usd: result.cost_saved_usd,
        cache_hit: result.cache_hit,
        router_decision: result.router_decision,
        guardrail_status: result.guardrail_status,
        citations: result.citations || [],
      },
    };

    return NextResponse.json(completion, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key",
      },
    });
  } catch (err: any) {
    return NextResponse.json(
      {
        error: {
          message: err.message || "Internal server error in Prometheus completions router",
          type: "internal_error",
        },
      },
      { status: 500 }
    );
  }
}