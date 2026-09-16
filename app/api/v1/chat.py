"""POST /api/v1/chat Ã¢â‚¬â€ the 12-step agentic gateway pipeline.

Pipeline order (SPEC "CHAT PIPELINE REQUIREMENTS"):

accept -> validate -> auth (X-API-Key) -> rate limit -> budget/kill-switch ->
guardrails -> Router Agent -> semantic cache -> hit | miss (RAG -> LLM ->
cache write -> Evaluator -> cost log) -> audit -> response.

``run_chat_pipeline`` is exported so the evaluation harness can drive the
same in-process pipeline (DECISIONS B17 / D10).
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC
from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.evaluator_agent import EvalResult
from app.agents.evaluator_agent import evaluate as evaluator_evaluate
from app.agents.guardrail_agent import check as guardrail_check
from app.agents.router_agent import RouterDecision
from app.agents.router_agent import decide as router_decide
from app.cache.cache_policy import should_cache
from app.cache.semantic_cache import SemanticCache
from app.core.config import settings
from app.core.errors import PrometheusError
from app.core.events import emit_sse_event
from app.core.security import require_api_key
from app.cost.pricing import estimate_cost
from app.cost.tracker import record_usage
from app.db.models import ApiKey, FailedRequest, Request
from app.db.session import get_db
from app.governance.audit import append as audit_append
from app.governance.budget import after_spend_recorded, get_budget_status
from app.governance.kill_switch import apply_to_decision, get_mode
from app.governance.policy_engine import get_policy
from app.observability.metrics import record_request
from app.observability.trace_store import add_trace_event
from app.providers.embeddings.base import get_embedder
from app.providers.llm.base import ProviderUnavailableError, get_provider
from app.rag.citations import build_citations
from app.rag.retriever import Retriever
from app.vector.base import get_vector_store

router = APIRouter()

REFUSAL_TEMPLATE = (
    "This request was blocked by Prometheus guardrails ({reasons}). "
    "No model call was made and no cost was incurred."
)
KILL_SWITCH_TEMPLATE = "This request was blocked by the active kill switch ({reason})."


class ChatRequest(BaseModel):
    """Chat request body (Pydantic v2 validation)."""

    query: str = Field(min_length=1, max_length=8000)
    model: str | None = Field(default=None, max_length=64)
    provider: str | None = Field(default=None, max_length=32)
    metadata: dict[str, Any] | None = None


def _chat_response(
    *,
    request_id: str,
    answer: str,
    provider: str,
    model: str,
    router_decision: str,
    cache_hit: bool,
    estimated_cost_usd: float,
    cost_saved_usd: float,
    latency_ms: int,
    input_tokens: int,
    output_tokens: int,
    guardrail_status: str,
    evaluation_score: float | None,
    citations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the exact 15-field chat response schema from the spec."""
    return {
        "request_id": request_id,
        "answer": answer,
        "provider": provider,
        "model": model,
        "router_decision": router_decision,
        "cache_hit": cache_hit,
        "estimated_cost_usd": round(float(estimated_cost_usd), 6),
        "cost_saved_usd": round(float(cost_saved_usd), 6),
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "guardrail_status": guardrail_status,
        "evaluation_score": evaluation_score,
        "citations": citations,
        "trace_url": f"/api/v1/traces/{request_id}",
    }


def _store_request_row(
    db: Session,
    *,
    request_id: str,
    api_key: ApiKey | None,
    response: dict[str, Any],
    status: str = "completed",
    error_code: str | None = None,
    idempotency_key: str | None = None,
) -> None:
    """Update the placeholder request row with final pipeline results.

    A minimal row is inserted at the start of ``run_chat_pipeline`` so that
    trace-event and usage-record FK references to ``requests.request_id`` are
    satisfied immediately (Postgres enforces FKs on INSERT, unlike SQLite).
    """
    row = db.scalar(select(Request).where(Request.request_id == request_id))
    if row is None:
        row = Request(request_id=request_id)
        db.add(row)
    row.organization_id = getattr(api_key, "organization_id", None)
    row.idempotency_key = idempotency_key
    row.api_key_id = getattr(api_key, "id", None)
    row.model = response.get("model")
    row.provider = response.get("provider")
    row.router_decision = response.get("router_decision")
    row.cache_hit = bool(response.get("cache_hit"))
    row.guardrail_status = response.get("guardrail_status")
    row.input_tokens = int(response.get("input_tokens") or 0)
    row.output_tokens = int(response.get("output_tokens") or 0)
    row.latency_ms = int(response.get("latency_ms") or 0)
    row.estimated_cost_usd = float(response.get("estimated_cost_usd") or 0.0)
    row.cost_saved_usd = float(response.get("cost_saved_usd") or 0.0)
    row.evaluation_score = response.get("evaluation_score")
    row.status = status
    row.response_json = response
    row.error_code = error_code
    db.commit()


def _store_failed_request(
    db: Session,
    *,
    request_id: str,
    api_key: ApiKey | None,
    error_type: str,
    error_message: str,
    payload_masked: dict[str, Any] | None = None,
) -> None:
    """Dead-letter table write (reliability requirements)."""
    row = FailedRequest(
        request_id=request_id,
        api_key_id=getattr(api_key, "id", None),
        error_type=error_type,
        error_message=error_message,
        retry_count=0,
        payload_masked=payload_masked or {},
    )
    db.add(row)
    db.commit()


def _build_retriever(db: Session) -> Retriever:
    return Retriever(lambda: db, get_embedder(), get_vector_store())


def _build_cache(db: Session, policy_version: int, kb_provider: Any) -> SemanticCache:
    return SemanticCache(
        lambda: db,
        policy_version_provider=lambda: policy_version,
        kb_version_provider=kb_provider,
    )


def run_chat_pipeline(
    query: str,
    model: str | None = None,
    provider: str | None = None,
    api_key: ApiKey | None = None,
    request_id: str | None = None,
    idempotency_key: str | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    """Execute the full chat pipeline and return the 15-field response dict.

    ``api_key`` must be an ``ApiKey`` ORM row (id + role + name). ``db`` is the
    request-scoped session used for request/failed-request rows; trace events,
    usage records, audits and SSE events use their own short-lived sessions
    (transactional-outbox design, B2).
    """
    from app.db.session import SessionLocal

    own_session = db is None
    if db is None:
        db = SessionLocal()

    request_id = request_id or f"req_{uuid.uuid4().hex[:16]}"
    if isinstance(api_key, str):
        # Accept a raw key string (eval harness / scripts resolve it here).
        from app.core.security import hash_api_key as _hash_api_key

        with SessionLocal() as _key_session:
            api_key = _key_session.scalar(
                select(ApiKey).where(ApiKey.key_hash == _hash_api_key(api_key))
            )
        if api_key is None:
            raise PrometheusError("Invalid API key", code="invalid_api_key", status_code=401)
    started = time.perf_counter()

    def _elapsed_ms() -> int:
        return int((time.perf_counter() - started) * 1000)

    # --- Insert placeholder Request row so trace-event / usage-record FKs
    #     pointing to requests.request_id are satisfied immediately.
    #     Postgres enforces FK constraints on INSERT (SQLite did not).
    db.add(Request(request_id=request_id, status="in_progress"))
    db.commit()

    # --- idempotent replay (B5): same key -> same stored response ------------
    if idempotency_key:
        from datetime import datetime, timedelta

        cutoff = datetime.now(UTC) - timedelta(
            seconds=int(settings.idempotency_ttl_seconds)
        )
        existing = db.scalar(
            select(Request)
            .where(
                Request.idempotency_key == idempotency_key,
                Request.api_key_id == getattr(api_key, "id", None),
                Request.created_at >= cutoff,
            )
            .order_by(Request.created_at.desc())
        )
        if existing is not None and existing.response_json:
            add_trace_event(
                request_id,
                "idempotent_replay",
                metadata={"original_request_id": existing.request_id},
            )
            audit_append(
                getattr(api_key, "name", "api") or "api",
                getattr(api_key, "role", "viewer") or "viewer",
                "chat.replay",
                "chat",
                request_id=request_id,
                metadata={"original_request_id": existing.request_id},
            )
            return existing.response_json

    # --- 1. request_received -------------------------------------------------
    add_trace_event(request_id, "request_received")
    emit_sse_event("request_started", {"query_length": len(query)}, request_id=request_id)

    # --- 3. auth_checked -----------------------------------------------------
    if api_key is None:
        add_trace_event(request_id, "auth_checked", status="error")
        raise PrometheusError("Missing API key", code="missing_api_key", status_code=401)
    add_trace_event(request_id, "auth_checked", metadata={"role": api_key.role})

    # --- 4. rate_limit_checked (enforced by middleware) ----------------------
    add_trace_event(request_id, "rate_limit_checked")

    # --- 5. budget_checked + kill switch -------------------------------------
    policy, policy_version = get_policy()
    budget_status = get_budget_status()
    mode = get_mode()
    add_trace_event(
        request_id,
        "budget_checked",
        metadata={
            "budget_status": budget_status.get("status"),
            "kill_switch_mode": mode,
            "daily_spend_usd": budget_status.get("daily_spend_usd"),
            "daily_budget_usd": budget_status.get("daily_budget_usd"),
        },
    )
    if mode == "block_all":
        raise PrometheusError(
            "Kill switch active: block_all",
            code="kill_switch_block_all",
            status_code=403,
        )

    # --- 6. guardrail_checked -------------------------------------------------
    est_input = max(1, len(query) // 4)
    est_cost = estimate_cost(settings.default_model, est_input, 64)
    gr = guardrail_check(query, policy=policy, estimated_request_cost=est_cost)
    query_used = gr.masked_text if gr.masked_text else query
    guardrail_status = "passed"
    if gr.blocked:
        add_trace_event(
            request_id,
            "guardrail_checked",
            status="blocked",
            metadata={"reasons": gr.reasons, "risk_level": gr.risk_level},
        )
        answer = REFUSAL_TEMPLATE.format(reasons=", ".join(gr.reasons))
        response = _chat_response(
            request_id=request_id,
            answer=answer,
            provider="none",
            model="",
            router_decision="REJECT",
            cache_hit=False,
            estimated_cost_usd=0.0,
            cost_saved_usd=0.0,
            latency_ms=_elapsed_ms(),
            input_tokens=0,
            output_tokens=0,
            guardrail_status="blocked",
            evaluation_score=None,
            citations=[],
        )
        _store_request_row(
            db, request_id=request_id, api_key=api_key, response=response,
            status="blocked", error_code="guardrail_blocked",
            idempotency_key=idempotency_key,
        )
        audit_append(
            getattr(api_key, "name", "api") or "api",
            api_key.role,
            "guardrail.blocked",
            "chat",
            request_id=request_id,
            metadata={"reasons": gr.reasons},
        )
        add_trace_event(request_id, "cost_logged", metadata={"cost_usd": 0.0})
        add_trace_event(request_id, "response_returned", duration_ms=_elapsed_ms())
        return response
    if gr.pii_found:
        guardrail_status = "masked"
    add_trace_event(
        request_id,
        "guardrail_checked",
        metadata={
            "pii_found": gr.pii_found,
            "pii_masked": bool(gr.masked_text),
            "reasons": gr.reasons,
        },
    )

    # --- 7. router_decided ----------------------------------------------------
    decision: RouterDecision = router_decide(
        query_used,
        budget_status=budget_status.get("status", "normal"),
        policy=policy,
        cache_similarity=0.0,
        guardrail_risk=gr.risk_level,
    )
    add_trace_event(
        request_id,
        "router_decided",
        metadata={
            "decision": decision.decision,
            "model": decision.model,
            "complexity": decision.complexity,
            "category": decision.category,
            "risk_level": decision.risk_level,
            "reason": decision.reason,
        },
    )
    model = model or decision.model
    # Caller-supplied model must respect the policy allowlist (B4/MEDIUM fix).
    allowed_models = policy.get("allowed_models") or []
    if model and model not in allowed_models:
        raise PrometheusError(
            f"Model {model!r} is not allowed by the active policy",
            code="model_not_allowed",
            status_code=403,
        )
    # Expensive-model daily cap (B8) enforced in the request path.
    if model in set(policy.get("expensive_models") or []):
        from sqlalchemy import func

        from app.db.models import UsageRecord, utc_today

        used = db.scalar(
            select(func.count(UsageRecord.id)).where(
                UsageRecord.model == model, UsageRecord.date == utc_today()
            )
        )
        if int(used or 0) >= int(policy.get("expensive_model_limit_per_day", 20)):
            raise PrometheusError(
                "Daily limit reached for expensive models",
                code="expensive_model_limit_reached",
                status_code=403,
            )
    # Kill-switch gating on the EFFECTIVE model (a caller-requested override
    # must not bypass cheap_only/cache_only enforcement).
    final_decision, blocked_reason = apply_to_decision(decision.decision, model)
    if blocked_reason:
        response = _chat_response(
            request_id=request_id,
            answer=KILL_SWITCH_TEMPLATE.format(reason=blocked_reason),
            provider="none",
            model="",
            router_decision=final_decision,
            cache_hit=False,
            estimated_cost_usd=0.0,
            cost_saved_usd=0.0,
            latency_ms=_elapsed_ms(),
            input_tokens=0,
            output_tokens=0,
            guardrail_status="blocked_kill_switch",
            evaluation_score=None,
            citations=[],
        )
        _store_request_row(
            db, request_id=request_id, api_key=api_key, response=response,
            status="blocked", error_code=blocked_reason,
            idempotency_key=idempotency_key,
        )
        audit_append(
            getattr(api_key, "name", "api") or "api",
            api_key.role,
            "kill_switch.blocked",
            "chat",
            request_id=request_id,
            metadata={"reason": blocked_reason},
        )
        add_trace_event(request_id, "cost_logged", metadata={"cost_usd": 0.0})
        add_trace_event(request_id, "response_returned", duration_ms=_elapsed_ms())
        return response

    provider = provider or (settings.llm_provider or "mock")
    retriever = _build_retriever(db)
    cache = _build_cache(db, policy_version, retriever.kb_version)

    # --- 8. cache_checked -----------------------------------------------------
    embedder = get_embedder()
    embedding = embedder.embed([query_used])[0]
    hit = None
    if policy.get("require_cache_check", True):
        hit = cache.lookup(query_used, embedding)
    add_trace_event(
        request_id,
        "cache_checked",
        metadata={
            "cache_hit": bool(hit),
            "similarity": hit.get("similarity") if hit else None,
        },
    )

    # --- 9. cache hit: return cached answer + cost saved ----------------------
    if hit is not None:
        cost_saved = float(hit.get("cost_saved_usd") or 0.0)
        response = _chat_response(
            request_id=request_id,
            answer=hit.get("answer") or "",
            provider="cache",
            model=hit.get("model") or model,
            router_decision=final_decision,
            cache_hit=True,
            estimated_cost_usd=0.0,
            cost_saved_usd=cost_saved,
            latency_ms=_elapsed_ms(),
            input_tokens=int(hit.get("input_tokens") or 0),
            output_tokens=int(hit.get("output_tokens") or 0),
            guardrail_status=guardrail_status,
            evaluation_score=None,
            citations=[],
        )
        record_usage(
            request_id=request_id,
            model=response["model"],
            provider="cache",
            input_tokens=response["input_tokens"],
            output_tokens=response["output_tokens"],
            cache_read_tokens=response["input_tokens"],
            cost_usd=0.0,
            cache_saved_usd=cost_saved,
        )
        _store_request_row(
            db, request_id=request_id, api_key=api_key, response=response,
            idempotency_key=idempotency_key,
        )
        audit_append(
            getattr(api_key, "name", "api") or "api",
            api_key.role,
            "chat.request",
            "chat",
            request_id=request_id,
            metadata={
                "model": response["model"],
                "router_decision": final_decision,
                "cache_hit": True,
                "cost_saved_usd": cost_saved,
            },
        )
        record_request(
            model=response["model"],
            router_decision=final_decision,
            cache_hit=True,
            latency_seconds=_elapsed_ms() / 1000.0,
            input_tokens=response["input_tokens"],
            output_tokens=response["output_tokens"],
            cost_usd=0.0,
            cache_saved_usd=cost_saved,
        )
        add_trace_event(
            request_id, "cost_logged",
            metadata={"cost_usd": 0.0, "cost_saved_usd": cost_saved},
        )
        add_trace_event(request_id, "response_returned", duration_ms=_elapsed_ms())
        return response

    # --- cache_only kill switch: a miss is refused without any LLM call (B6) ---
    if get_mode() == "cache_only":
        response = _chat_response(
            request_id=request_id,
            answer=KILL_SWITCH_TEMPLATE.format(reason="kill_switch_cache_only"),
            provider="none",
            model="",
            router_decision="CACHE_ONLY",
            cache_hit=False,
            estimated_cost_usd=0.0,
            cost_saved_usd=0.0,
            latency_ms=_elapsed_ms(),
            input_tokens=0,
            output_tokens=0,
            guardrail_status="blocked_kill_switch",
            evaluation_score=None,
            citations=[],
        )
        _store_request_row(
            db, request_id=request_id, api_key=api_key, response=response,
            status="blocked", error_code="kill_switch_cache_only",
            idempotency_key=idempotency_key,
        )
        audit_append(
            getattr(api_key, "name", "api") or "api",
            api_key.role,
            "kill_switch.blocked",
            "chat",
            request_id=request_id,
            metadata={"reason": "kill_switch_cache_only"},
        )
        add_trace_event(request_id, "cost_logged", metadata={"cost_usd": 0.0})
        add_trace_event(request_id, "response_returned", duration_ms=_elapsed_ms())
        return response

    # --- 10. cache miss: RAG -> LLM -> evaluator -> cache write ---------------
    chunks: list[dict[str, Any]] = []
    if policy.get("require_rag", True):
        chunks = retriever.retrieve(query_used, top_k=5)
    citations = build_citations(chunks)
    add_trace_event(
        request_id, "retrieval_completed", metadata={"chunks": len(chunks)}
    )

    system = (
        "You are Prometheus, an agentic AI governance and FinOps control plane. "
        "Answer grounded in the provided context and cite sources as [n]. "
        "Be concise, factual, and safe."
    )
    context = "\n\n".join(
        f"[{i + 1}] {c.get('content', '')}" for i, c in enumerate(chunks)
    )
    from .finops import compress_prompt
    compressed_query = compress_prompt(query_used)
    prompt = (
        f"Context:\n{context}\n\nQuestion: {compressed_query}\n\n"
        if context
        else f"Question: {compressed_query}\n"
    )

    try:
        llm = get_provider(provider)
        resp = llm.generate(
            prompt,
            model=model,
            system=system,
            max_tokens=int(policy.get("max_output_tokens", 500) or 500),
            temperature=0.3,
        )
    except (ProviderUnavailableError, Exception) as exc:  # noqa: BLE001 - controlled
        # Intelligent Semantic Fallback Cascade
        if model != settings.default_model:
            add_trace_event(
                request_id, 
                "semantic_fallback_triggered", 
                metadata={"original_model": model, "error": str(exc)[:200], "fallback_model": settings.default_model}
            )
            model = settings.default_model
            try:
                resp = llm.generate(
                    prompt,
                    model=model,
                    system=system,
                    max_tokens=int(policy.get("max_output_tokens", 500) or 500),
                    temperature=0.3,
                )
            except Exception as inner_exc:
                exc = inner_exc
                resp = None
        else:
            resp = None

        if resp is None:
            _store_failed_request(
                db,
                request_id=request_id,
                api_key=api_key,
                error_type="provider_unavailable",
                error_message=str(exc)[:500],
            )
            add_trace_event(request_id, "llm_called", status="error", metadata={"error": str(exc)[:200]})
            audit_append(
                getattr(api_key, "name", "api") or "api",
                api_key.role,
                "chat.failed",
                "chat",
                request_id=request_id,
                metadata={"error_type": "provider_unavailable"},
            )
            raise PrometheusError(
                "The LLM provider is currently unavailable. Request stored in the dead-letter table.",
                code="provider_unavailable",
                status_code=503,
            ) from exc

    answer = resp.text
    input_tokens = resp.input_tokens
    output_tokens = resp.output_tokens
    cost = estimate_cost(model, input_tokens, output_tokens)
    add_trace_event(
        request_id,
        "llm_called",
        metadata={
            "model": model,
            "provider": llm.provider_name,
            "latency_ms": resp.latency_ms,
        },
    )

    # --- evaluator ------------------------------------------------------------
    evaluation_score: float | None = None
    eval_result: EvalResult | None = None
    retried = False
    if policy.get("require_evaluation", True):
        eval_result = evaluator_evaluate(
            request_id=request_id,
            query=query_used,
            answer=answer,
            citations=citations,
            cost_usd=cost,
            model=model,
            router_decision=final_decision,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            policy=policy,
        )
        evaluation_score = eval_result.overall_score
        # Optional one retry with the strong model when a cheap answer failed.
        if (
            not eval_result.passed
            and final_decision == "CHEAP_MODEL"
            and budget_status.get("status") != "exceeded"
        ):
            strong_model = settings.strong_model
            try:
                resp2 = llm.generate(
                    prompt, model=strong_model, system=system,
                    max_tokens=int(policy.get("max_output_tokens", 500) or 500),
                )
                answer = resp2.text
                input_tokens = resp2.input_tokens
                output_tokens = resp2.output_tokens
                cost = estimate_cost(strong_model, input_tokens, output_tokens)
                retried = True
                eval_result = evaluator_evaluate(
                    request_id=request_id,
                    query=query_used,
                    answer=answer,
                    citations=citations,
                    cost_usd=cost,
                    model=strong_model,
                    router_decision="STRONG_MODEL",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    policy=policy,
                )
                evaluation_score = eval_result.overall_score
                model = strong_model
            except Exception:  # noqa: BLE001 - keep the original answer on retry failure
                pass
        add_trace_event(
            request_id,
            "evaluation_completed",
            metadata={
                "overall_score": evaluation_score,
                "passed": bool(eval_result.passed),
                "retried_with_strong_model": retried,
                "evaluation_failed": not eval_result.passed,
            },
        )

    # --- cache write (never cache refusals/blocked) ---------------------------
    cached = False
    if should_cache(
        final_decision,
        guardrail_status,
        eval_result.passed if eval_result is not None else True,
        policy,
    ):
        cache.put(
            query_used,
            embedding,
            answer,
            model,
            input_tokens,
            output_tokens,
            estimated_cost_usd=cost,
        )
        cached = True

    # --- cost log + budget re-evaluation --------------------------------------
    record_usage(
        request_id=request_id,
        model=model,
        provider=provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_write_tokens=input_tokens if cached else 0,
        cost_usd=cost,
        cache_saved_usd=0.0,
    )
    after_spend_recorded()
    add_trace_event(request_id, "cost_logged", metadata={"cost_usd": cost, "cached": cached})

    response = _chat_response(
        request_id=request_id,
        answer=answer,
        provider=provider,
        model=model,
        router_decision=final_decision,
        cache_hit=False,
        estimated_cost_usd=cost,
        cost_saved_usd=0.0,
        latency_ms=_elapsed_ms(),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        guardrail_status=guardrail_status,
        evaluation_score=evaluation_score,
        citations=citations,
    )

    # --- 11. audit + persist ------------------------------------------------
    _store_request_row(
        db, request_id=request_id, api_key=api_key, response=response,
        idempotency_key=idempotency_key,
    )
    audit_append(
        getattr(api_key, "name", "api") or "api",
        api_key.role,
        "chat.request",
        "chat",
        request_id=request_id,
        metadata={
            "model": model,
            "provider": provider,
            "router_decision": final_decision,
            "cache_hit": False,
            "cost_usd": cost,
            "evaluation_score": evaluation_score,
        },
        organization_id=getattr(api_key, "organization_id", None),
    )

    # --- 12. response_returned ----------------------------------------------
    record_request(
        model=model,
        router_decision=final_decision,
        cache_hit=False,
        latency_seconds=_elapsed_ms() / 1000.0,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
        cache_saved_usd=0.0,
    )
    add_trace_event(request_id, "response_returned", duration_ms=_elapsed_ms())
    if own_session:
        db.close()
    return response


@router.post("/chat")
def chat(
    body: ChatRequest,
    key: ApiKey = Depends(require_api_key),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Chat endpoint: runs the full pipeline and returns the spec response."""
    request_id = f"req_{uuid.uuid4().hex[:16]}"
    return run_chat_pipeline(
        body.query,
        model=body.model,
        provider=body.provider,
        api_key=key,
        request_id=request_id,
        idempotency_key=x_idempotency_key,
        db=db,
    )

class ChatCompletionMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "default"
    messages: list[ChatCompletionMessage]
    stream: bool = False

@router.post("/chat/completions")
def openai_chat_completions(
    req: ChatCompletionRequest,
    api_key: ApiKey = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """OpenAI-compatible chat completion endpoint that wraps the Prometheus pipeline."""
    # Concatenate messages (a simple implementation for the pipeline)
    query = "\\n".join([f"{m.role}: {m.content}" for m in req.messages])
    
    # Execute Prometheus full pipeline
    result = run_chat_pipeline(query, model=req.model, api_key=api_key, db=db)
    
    # Translate Prometheus response to OpenAI format
    return {
        "id": result["request_id"],
        "object": "chat.completion",
        "created": int(time.time()),
        "model": result["model"],
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result["answer"],
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": result["input_tokens"],
            "completion_tokens": result["output_tokens"],
            "total_tokens": result["input_tokens"] + result["output_tokens"]
        },
        # Custom extension to expose Prometheus telemetry
        "prometheus_metadata": {
            "cost_usd": result["estimated_cost_usd"],
            "cache_hit": result["cache_hit"],
            "latency_ms": result["latency_ms"],
            "router_decision": result["router_decision"],
            "guardrail_status": result["guardrail_status"],
            "trace_url": result["trace_url"]
        }
    }
