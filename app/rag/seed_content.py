"""Seed documents for the RAG knowledge base (demo-facing).

Five documents matching the spec's seed list exactly:

    doc_01 AI Cost Governance
    doc_02 LLM Cache Optimization
    doc_03 AWS Bedrock Cost Controls
    doc_04 AI Guardrails Overview
    doc_05 FinOps for AI

Each document is 3-5 paragraphs of substantive, accurate content so the
demo answers are grounded and credible. ``ingest_seed_documents(retriever)``
loads them through the RAG pipeline in one call.
"""
from __future__ import annotations

from typing import Any

__all__ = ["SEED_DOCUMENTS", "ingest_seed_documents"]

SEED_DOCUMENTS: list[dict[str, Any]] = [
    {
        "document_id": "doc_01",
        "title": "AI Cost Governance",
        "metadata": {"source": "seed", "topic": "cost-governance", "doc_type": "reference"},
        "content": (
            "AI cost governance is the discipline of aligning model spend with business value. "
            "Every LLM call consumes tokens that carry a real price, and without governance that "
            "spend grows silently across teams, models and use cases. Governance makes each call "
            "accountable to an owner by coupling budgets, policies and observability into a single "
            "control loop.\n\n"
            "A practical governance stack has four layers. First, budgets: a daily budget per "
            "environment, a request-level budget cap so no single prompt can spike the bill, and "
            "per-model spend limits that prevent expensive models from dominating. Second, policy: "
            "allowed model lists, required cache checks, required RAG grounding and human-approval "
            "gates for policy changes. Third, enforcement: kill-switch modes that downgrade the "
            "gateway to cache-only, cheap-only or block-all when budgets are exceeded. Fourth, "
            "auditing: every policy change and budget transition is recorded immutably.\n\n"
            "Observability is the foundation of governance. Per-request cost, token counts, latency "
            "and cache savings must be attributed to team, model and use case so chargeback and "
            "showback work. A dashboard that shows daily spend against the budget, model-wise "
            "breakdowns and cache hit rates turns vague anxiety about AI cost into concrete numbers "
            "managers can act on.\n\n"
            "Governance also needs escalation semantics. Budget states progress from normal through "
            "warning and critical to exceeded; crossing a threshold triggers alerts, restricts "
            "expensive models and eventually activates the kill switch for subsequent requests. "
            "Crucially, an in-flight request is never aborted mid-call: tokens already spent cannot "
            "be unspent, so enforcement gates what happens next rather than interrupting work that "
            "has already started."
        ),
    },
    {
        "document_id": "doc_02",
        "title": "LLM Cache Optimization",
        "metadata": {"source": "seed", "topic": "llm-cache", "doc_type": "reference"},
        "content": (
            "LLM traffic is surprisingly repetitive. Support questions, onboarding FAQs and "
            "operational lookups are asked over and over with slight rewording, and each repetition "
            "pays full token prices for near-identical answers. Semantic caching exploits this by "
            "storing prior answers keyed by embedding similarity rather than exact text match, so a "
            "near-duplicate question reuses the previous response.\n\n"
            "A semantic cache works like this: the query is embedded into a vector, and the cache "
            "scans non-expired entries for the highest cosine similarity. If the best match clears "
            "the similarity threshold, the stored answer is returned with the original tokens and "
            "costs logged as saved. If not, the pipeline generates a fresh answer and stores it for "
            "the next similar query. Thresholds around 0.82 balance precision (avoiding wrong "
            "matches) against recall (catching reworded questions).\n\n"
            "Versioning keeps the cache correct. Entries are stamped with the policy version, the "
            "knowledge-base version and a cache version; when a policy changes, a document is "
            "ingested, or the embedding configuration changes, stale entries become invisible and "
            "are swept. TTLs add a second expiry dimension so answers do not go stale silently. "
            "Hit and miss counts, cost saved and entry counts feed the cache-stats endpoint.\n\n"
            "The economics are strong: a cache read costs a fraction of a full generation (the B11 "
            "mock catalog prices cache reads at about a fifth of the input rate), so hit rates of "
            "30-70 percent on FAQ-heavy workloads cut both spend and latency dramatically. The "
            "trade-offs are staleness and safety: PII-masked or blocked responses must never be "
            "cached, which is why cacheability is decided by an explicit policy check after "
            "guardrails and evaluation."
        ),
    },
    {
        "document_id": "doc_03",
        "title": "AWS Bedrock Cost Controls",
        "metadata": {"source": "seed", "topic": "aws-bedrock", "doc_type": "reference"},
        "content": (
            "Amazon Bedrock is a managed service that serves foundation models from Anthropic, "
            "Amazon and other providers through one API, billing per token on demand. Model classes "
            "span a wide price range: the cheap Haiku tier is ideal for classification and short "
            "FAQ answers, Sonnet-class models handle reasoning and long-form generation, and Titan "
            "models provide embeddings for retrieval. Choosing the right class for each request is "
            "the single biggest cost lever.\n\n"
            "Model routing is where a gateway earns its keep. Short, factual questions should go to "
            "the cheapest adequate model; complex reasoning justifies a stronger model. The router "
            "in Project Prometheus classifies queries deterministically and, together with the "
            "request budget cap, prevents expensive models from being selected for trivial work. "
            "Request-level and daily budgets are enforced before the call, so a single runaway "
            "prompt cannot blow the budget.\n\n"
            "Capacity choices matter at scale. On-demand inference is fine for spiky, low-volume "
            "traffic; provisioned throughput reserves capacity for sustained load and can be cheaper "
            "when utilization is high. Cross-region inference profiles add resilience, and "
            "invocation logging plus CloudWatch metrics give per-model cost and latency telemetry. "
            "Alarms wired to budgets convert usage into alerts before it becomes a surprise bill.\n\n"
            "Project Prometheus models this production path faithfully: the Bedrock provider "
            "lazily imports boto3, maps bedrock-cheap and bedrock-strong to Haiku- and Sonnet-class "
            "model IDs via environment variables, retries transient failures with exponential "
            "backoff and surfaces clean, controlled errors when AWS credentials are absent. The "
            "local demo never needs AWS, but the production path is real."
        ),
    },
    {
        "document_id": "doc_04",
        "title": "AI Guardrails Overview",
        "metadata": {"source": "seed", "topic": "ai-guardrails", "doc_type": "reference"},
        "content": (
            "AI guardrails are policy enforcement points around model calls, applied both before "
            "and after the model runs. They protect the organization: the data it ingests, the "
            "content it serves and the models it pays for. Without guardrails, a gateway is just a "
            "billing pipe; with them, it is a governed platform.\n\n"
            "Input-side checks detect personal data and abuse. PII detection flags emails, phone "
            "numbers, credit card numbers (with Luhn validation), Aadhaar-like identifiers and "
            "secret/token patterns; when masking is enabled, the sensitive values are replaced and "
            "the pipeline continues. Unsafe-content screening blocks violence, self-harm and hate "
            "material; prompt-injection detection catches attempts to override system instructions; "
            "restricted-topic checks stop regulated or harmful requests at the door.\n\n"
            "Enforcement semantics matter. Blocking is for unsafe content, injection attempts and "
            "restricted topics: the request returns a safe refusal, no expensive model is called, "
            "and the event is audited. Masking is for PII when policy allows: the request proceeds "
            "with sensitive data scrubbed. Budget violations are treated as guardrail failures too "
            "- a request that would exceed its cost cap is downgraded or refused before the call.\n\n"
            "Every guardrail decision is written to the audit trail with the reason, the risk level "
            "and the masked payload, so security and compliance teams can review what was blocked "
            "and why. Guardrails also feed the cache policy: blocked and masked responses are never "
            "cached, preventing unsafe or personal content from being replayed to other users."
        ),
    },
    {
        "document_id": "doc_05",
        "title": "FinOps for AI",
        "metadata": {"source": "seed", "topic": "finops", "doc_type": "reference"},
        "content": (
            "FinOps for AI applies the cloud-finance operating model to model spend: the inform, "
            "optimize, operate cycle. Inform means measuring unit economics - cost per query, per "
            "model, per team - so everyone sees what AI actually costs. Optimize means attacking "
            "waste: routing to cheaper models, raising cache hit rates, right-sizing capacity and "
            "retiring unused capability. Operate means continuous improvement with verification, "
            "not one-off cleanup.\n\n"
            "Unit economics reframe the conversation. A support chatbot handling a thousand queries "
            "a day is not an abstract AI cost; it is 1,000 requests at a known price per request, "
            "with a measurable cache hit rate and an identifiable share of expensive-model usage. "
            "Once those numbers exist, optimization targets write themselves.\n\n"
            "The optimization playbook for LLMs is short and high-leverage. Route simple queries to "
            "cheap models first - it is usually the largest saving with the least risk. Raise the "
            "cache threshold or TTL when hit rates are low and similarity matches are safe. Block or "
            "quarantine models whose cost per useful token is out of line. Each change should carry "
            "an expected monthly saving, a risk level and a latency impact so humans can approve "
            "with confidence.\n\n"
            "Verification closes the loop. A FinOps agent that proposes a routing policy change "
            "estimates the saving, requests approval, applies the policy and then measures actual "
            "cost and hit-rate deltas on subsequent requests. Savings that cannot be verified are "
            "just hypotheses. This agentic approach - detect, hypothesize, simulate, estimate, "
            "approve, apply, verify, audit - is what turns FinOps from a spreadsheet exercise into "
            "a continuous, auditable optimization engine."
        ),
    },
]


def ingest_seed_documents(retriever: Any) -> dict[str, Any]:
    """Ingest all seed documents through the RAG pipeline.

    ``retriever`` is an ``app.rag.retriever.Retriever`` instance. Returns a
    summary dict ``{documents_ingested, chunks_created, kb_version, documents}``.
    """
    results = []
    total_chunks = 0
    for document in SEED_DOCUMENTS:
        result = retriever.ingest(
            document["document_id"],
            document["title"],
            document["content"],
            document.get("metadata"),
        )
        results.append(result)
        total_chunks += int(result.get("chunks_created", 0))
    return {
        "documents_ingested": len(SEED_DOCUMENTS),
        "chunks_created": total_chunks,
        "kb_version": retriever.kb_version(),
        "documents": [document["document_id"] for document in SEED_DOCUMENTS],
    }
