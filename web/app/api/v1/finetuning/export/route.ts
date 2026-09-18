import { NextRequest, NextResponse } from "next/server";

const SEED_PAIRS = [
  {
    query: "Explain how Prometheus semantic caching eliminates cloud model spend.",
    answer: "Prometheus semantic caching computes high-dimensional vector embeddings of incoming prompts and queries an indexed vector database (e.g. pgvector) using cosine similarity. If an incoming query has a similarity score >= 0.82 with an existing cached query, Prometheus returns the stored answer immediately in under 350ms for $0.00 cost, completely bypassing foundation model invocation.",
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
];

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const format = searchParams.get("format")?.toLowerCase() || "chatml";

  const lines = SEED_PAIRS.map((item) => {
    if (format === "alpaca") {
      return JSON.stringify({
        instruction: item.query,
        input: "",
        output: item.answer,
      });
    }
    if (format === "sharegpt") {
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

  const content = lines.join("\n");
  return new NextResponse(content, {
    status: 200,
    headers: {
      "Content-Type": "application/x-jsonlines; charset=utf-8",
      "Content-Disposition": `attachment; filename="prometheus_${format}_golden.jsonl"`,
    },
  });
}
