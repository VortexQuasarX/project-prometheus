import { NextRequest, NextResponse } from "next/server";

const GOLDEN_PAIRS = [
  {
    query: "Explain how Prometheus semantic caching eliminates cloud model spend.",
    answer: "Prometheus semantic caching computes high-dimensional vector embeddings of incoming prompts and queries an indexed vector database (e.g. pgvector) using cosine similarity. If an incoming query has a similarity score >= 0.82 with an existing cached query, Prometheus returns the stored answer immediately in under 30ms for $0.00 cost, completely bypassing foundation model invocation.",
  },
  {
    query: "What happens when an employee sends credit card numbers or PII into an LLM prompt?",
    answer: "Prometheus guardrails intercept the request during Stage 4 before any external model call. Regex and entity recognition filters detect the credit card or PII and either masks them (e.g. [REDACTED_CARD]) or safely rejects the prompt with zero cost incurred, logging the incident to the immutable audit ledger for compliance review.",
  },
  {
    query: "How does the Prometheus budget kill-switch prevent surprise AWS bills?",
    answer: "Prometheus tracks cumulative micro-dollar spending in real time. If a department or key reaches its configured warning ratio (70%), alerts fire to Slack and Discord. If spending hits the critical quota (90-100%), the automated circuit-breaker trips, cutting non-critical traffic or forcing fallback to zero-cost models to guarantee budget caps.",
  },
  {
    query: "Compare dense vector search against BM25 sparse lexical search in RAG pipelines.",
    answer: "Dense vector search embeds text into continuous semantic vector space, excelling at conceptual and thematic matching. BM25 sparse lexical search evaluates exact token frequencies and inverse document frequencies, excelling at rare keywords, acronyms, and product IDs. Prometheus Hybrid Search combines both using Reciprocal Rank Fusion (RRF) and Cross-Encoder re-ranking for optimal retrieval precision.",
  },
  {
    query: "How does Cross-Encoder re-ranking mitigate LLM hallucinations?",
    answer: "Dual-encoder bi-encoders calculate separate representations for queries and documents. Cross-encoders pass both query and chunk simultaneously through transformer cross-attention layers, scoring exact joint relevance. Prometheus prunes irrelevant chunks before prompt construction, drastically compressing the context window, reducing token billing, and preventing the model from hallucinating over noisy context.",
  },
  {
    query: "What is the role of Apache Kafka in Prometheus event streaming?",
    answer: "Prometheus decouples audit logging and telemetry ingestion from client proxy latency by asynchronously publishing events to managed Kafka topics: prometheus.requests for inference telemetry, prometheus.audit for regulatory compliance, prometheus.costs for departmental chargeback, and prometheus.requests.dlq for dead-letter queuing.",
  },
  {
    query: "How does QLoRA achieve 4-bit parameter-efficient fine-tuning?",
    answer: "QLoRA quantizes the base foundation model (e.g. Llama 3 8B) to 4-bit NormalFloat (NF4) precision with double quantization while maintaining 16-bit brain float computation. It freezes base model weights and only trains low-rank adapter matrices (r=16, alpha=32) across query, key, value, and projection layers, reducing VRAM footprint by 75% with zero quality degradation.",
  },
  {
    query: "Describe the Prometheus Horizontal Pod Autoscaler (HPA) policy in Kubernetes.",
    answer: "Prometheus defines a Kubernetes HPA resource with a minimum of 2 and maximum of 10 replicas. Scaling triggers evaluate average CPU utilization exceeding 70% and memory utilization exceeding 80%. A zero-trust NetworkPolicy enforces strict ingress to port 8000 and restricts egress exclusively to RDS PostgreSQL, Redis, Kafka, and external Bedrock endpoints over TLS 443.",
  },
];

function generateJsonl(format: string): string {
  const fmt = format.toLowerCase();
  const lines = GOLDEN_PAIRS.map((item) => {
    if (fmt === "alpaca") {
      return JSON.stringify({
        instruction: item.query,
        input: "",
        output: item.answer,
      });
    }
    if (fmt === "sharegpt") {
      return JSON.stringify({
        conversations: [
          { from: "human", value: item.query },
          { from: "gpt", value: item.answer },
        ],
      });
    }
    return JSON.stringify({
      messages: [
        { role: "system", content: "You are Prometheus AI, a specialized enterprise assistant." },
        { role: "user", content: item.query },
        { role: "assistant", content: item.answer },
      ],
    });
  });

  return lines.join("\n");
}

export async function POST(req: NextRequest) {
  let format = "chatml";
  try {
    const body = await req.json();
    if (body?.format) format = String(body.format);
  } catch {}

  const content = generateJsonl(format);
  return new NextResponse(content, {
    status: 200,
    headers: {
      "Content-Type": "application/x-jsonlines; charset=utf-8",
      "Content-Disposition": `attachment; filename="prometheus_lora_${format}.jsonl"`,
    },
  });
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const format = searchParams.get("format") || "chatml";

  const content = generateJsonl(format);
  return new NextResponse(content, {
    status: 200,
    headers: {
      "Content-Type": "application/x-jsonlines; charset=utf-8",
      "Content-Disposition": `attachment; filename="prometheus_lora_${format}.jsonl"`,
    },
  });
}
