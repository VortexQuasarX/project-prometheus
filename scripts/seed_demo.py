"""Deterministic, idempotent demo seed (scripts/seed_demo.py).

Recruiter-demo bootstrap for Project Prometheus. Seeds, in order:

1. ``init_db()`` — create tables + seed-if-empty (policy, docs, keys).
2. RAG ingestion of the five SEED_DOCUMENTS via ``Retriever`` (only when no
   document chunks exist, so repeated runs are no-ops for the KB).
3. Demo API keys ``prometheus-demo-admin-key`` (admin) and
   ``prometheus-demo-viewer-key`` (viewer) — SHA-256 hashed at rest, printed
   at the end. A usable ``ADMIN_API_KEY`` env value is honored as an extra
   admin key.
4. Default policy (SPEC JSON + ``expensive_models``) via the policy engine.
5. Usage history for the last 7 UTC days: 35-45 requests/day from
   ``random.Random(42)``, mock-small/mock-large mix, ~15-35% cache hits,
   daily spend landing in ~40-60% of the $2.00 daily budget. Request rows
   mirror the usage records so /metrics and /cost-report are coherent.
6. Three full 12-event trace timelines (small miss / large miss / cache hit).
7. One completed FinOps agent run (``run_demo_finops_001``, status
   ``verified``) with spec-shaped plan / steps / tool_calls rows + JSON.
8. One PENDING agent action — EXACTLY the SPEC example: action_id
   ``action_101``, title "Route simple queries to cheaper model",
   expected_monthly_saving_usd 18.4, risk_level "low",
   latency_impact "minimal", approval_required true, status "pending"
   (owned by a second run in ``waiting_approval`` so the state machine stays
   consistent).
9. One completed eval run (``eval_demo_seed_001``) with 8-key avg metrics —
   fabricated rows, not a live ``run_evals()`` (which needs the chat API
   slice and would be neither deterministic nor idempotent).
10. Audit events.

Determinism: fixed RNG seed; counts, costs, latencies and scores are fully
deterministic. The only wall-clock input is the UTC calendar date used to
anchor the "last 7 days" window (required for the budget dashboard to show
live spend); intra-day timestamps are fixed offsets.

Usage:
    python scripts/seed_demo.py          # from the repository root
"""

from __future__ import annotations

import random
import sys
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Any

# --- bootstrap: make `app` importable regardless of cwd ---------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.core.security import hash_api_key  # noqa: E402
from app.cost.pricing import cache_read_cost, estimate_cost  # noqa: E402
from app.db.init_db import init_db  # noqa: E402
from app.db.models import AgentRun, utcnow  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

DEMO_ADMIN_KEY = "prometheus-demo-admin-key"
DEMO_VIEWER_KEY = "prometheus-demo-viewer-key"

TRACE_EVENT_NAMES: tuple[str, ...] = (
    "request_received",
    "auth_checked",
    "rate_limit_checked",
    "budget_checked",
    "guardrail_checked",
    "router_decided",
    "cache_checked",
    "retrieval_completed",
    "llm_called",
    "evaluation_completed",
    "cost_logged",
    "response_returned",
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# API keys + policy
# ---------------------------------------------------------------------------


def _ensure_api_key(session: Any, raw: str, name: str, role: str) -> int:
    from app.db.models import ApiKey

    key_hash = hash_api_key(raw)
    row = session.query(ApiKey).filter_by(key_hash=key_hash).first()
    if row is None:
        row = ApiKey(key_hash=key_hash, name=name, role=role, is_active=True)
        session.add(row)
        session.commit()
        session.refresh(row)
    elif row.role != role:
        row.role = role
        session.commit()
    return int(row.id)


def _ensure_policy() -> tuple[dict[str, Any], int]:
    """Ensure an active default policy exists (spec JSON + expensive_models)."""
    from app.governance.policy_engine import get_policy

    policy, version = get_policy()
    return policy, version


# ---------------------------------------------------------------------------
# RAG ingestion
# ---------------------------------------------------------------------------


def _ingest_documents(session: Any) -> dict[str, Any]:
    """Ingest SEED_DOCUMENTS via the Retriever when chunks are missing."""
    from app.db.models import DocumentChunk

    existing = int(session.query(DocumentChunk).count())
    if existing > 0:
        return {"skipped": True, "reason": f"{existing} document chunks already present"}

    from app.providers.embeddings.mock_embeddings import MockEmbedder
    from app.rag.retriever import Retriever
    from app.rag.seed_content import ingest_seed_documents
    from app.vector.local_vector_store import LocalVectorStore

    retriever = Retriever(
        get_db=SessionLocal,
        embedder=MockEmbedder(),
        vector_store=LocalVectorStore(settings.data_path()),
    )
    return ingest_seed_documents(retriever)


# ---------------------------------------------------------------------------
# usage history (last 7 UTC days, fixed RNG)
# ---------------------------------------------------------------------------


def _make_request(rng: random.Random, day_index: int, seq: int, viewer_key_id: int, day_date: Any) -> dict[str, Any]:
    is_hit = rng.random() < rng.uniform(0.15, 0.35)
    model = "mock-small" if rng.random() < 0.6 else "mock-large"
    input_tokens = rng.randint(120, 2600)
    output_tokens = rng.randint(60, 1200)

    hour = 8 + (seq * 19) // 60
    minute = (seq * 19) % 60
    created_at = datetime.combine(day_date, time(hour=min(23, hour), minute=minute), tzinfo=UTC)

    if is_hit:
        cost = 0.0
        saved = max(0.0, estimate_cost(model, input_tokens, output_tokens) - cache_read_cost(model, input_tokens))
        router_decision = "CACHE_ONLY"
        latency = rng.randint(8, 25)
    else:
        cost = estimate_cost(model, input_tokens, output_tokens)
        saved = 0.0
        router_decision = "CHEAP_MODEL" if model == "mock-small" else "STRONG_MODEL"
        latency = rng.randint(80, 150) if model == "mock-small" else rng.randint(420, 640)

    return {
        "request_id": f"seed_req_{day_index:02d}_{seq:03d}",
        "api_key_id": viewer_key_id,
        "model": model,
        "provider": "mock",
        "router_decision": router_decision,
        "cache_hit": is_hit,
        "guardrail_status": "passed",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency,
        "estimated_cost_usd": round(cost, 6),
        "cost_saved_usd": round(saved, 6),
        "evaluation_score": round(rng.uniform(0.8, 0.97), 4),
        "status": "completed",
        "created_at": created_at,
        "date": created_at.date().isoformat(),
    }


def _generate_day(rng: random.Random, day_index: int, viewer_key_id: int, day_date: Any) -> list[dict[str, Any]]:
    """Generate one day of requests with total spend in [0.80, 1.20] USD."""
    best: list[dict[str, Any]] | None = None
    for _attempt in range(80):
        count = rng.randint(35, 45)
        requests = [_make_request(rng, day_index, seq, viewer_key_id, day_date) for seq in range(1, count + 1)]
        total = sum(request["estimated_cost_usd"] for request in requests)
        if 0.80 <= total <= 1.20:
            return requests
        best = requests
    return best or []


def _seed_usage_history(session: Any, viewer_key_id: int) -> dict[str, Any]:
    """Insert Request + UsageRecord rows for the last 7 UTC days."""
    from app.db.models import Request, UsageRecord

    existing = int(
        session.query(Request).filter(Request.request_id.like("seed_req_%")).count()
    )
    if existing > 0:
        return {"skipped": True, "reason": f"{existing} seeded requests already present"}

    rng = random.Random(42)
    today = utcnow().date()
    all_requests: list[dict[str, Any]] = []
    daily_spend: list[float] = []

    for day_index, offset in enumerate(range(6, -1, -1)):
        day_date = today - timedelta(days=offset)
        requests = _generate_day(rng, day_index, viewer_key_id, day_date)
        all_requests.extend(requests)
        daily_spend.append(round(sum(r["estimated_cost_usd"] for r in requests), 6))

        for request in requests:
            session.add(
                Request(
                    request_id=request["request_id"],
                    api_key_id=viewer_key_id,
                    model=request["model"],
                    provider=request["provider"],
                    router_decision=request["router_decision"],
                    cache_hit=request["cache_hit"],
                    guardrail_status=request["guardrail_status"],
                    input_tokens=request["input_tokens"],
                    output_tokens=request["output_tokens"],
                    latency_ms=request["latency_ms"],
                    estimated_cost_usd=request["estimated_cost_usd"],
                    cost_saved_usd=request["cost_saved_usd"],
                    evaluation_score=request["evaluation_score"],
                    status=request["status"],
                    created_at=request["created_at"],
                )
            )
            session.add(
                UsageRecord(
                    request_id=request["request_id"],
                    date=request["date"],
                    model=request["model"],
                    provider=request["provider"],
                    input_tokens=request["input_tokens"],
                    output_tokens=request["output_tokens"],
                    cache_read_tokens=request["input_tokens"] if request["cache_hit"] else 0,
                    cache_write_tokens=0 if request["cache_hit"] else request["input_tokens"],
                    cost_usd=request["estimated_cost_usd"],
                    cache_saved_usd=request["cost_saved_usd"],
                    created_at=request["created_at"],
                )
            )
    session.commit()
    return {
        "skipped": False,
        "requests": len(all_requests),
        "days": 7,
        "daily_spend_usd": daily_spend,
        "total_spend_usd": round(sum(daily_spend), 6),
        "requests_by_day": [
            sum(1 for r in all_requests if r["date"] == (today - timedelta(days=offset)).isoformat())
            for offset in range(6, -1, -1)
        ],
    }


# ---------------------------------------------------------------------------
# traces (3 full 12-event timelines)
# ---------------------------------------------------------------------------


def _seed_traces(session: Any, requests: list[dict[str, Any]]) -> dict[str, Any]:
    """Full 12-event timelines for a small miss, a large miss and a cache hit."""
    from app.db.models import TraceEvent

    def _pick(predicate: Any) -> dict[str, Any] | None:
        for request in requests:
            if predicate(request):
                return request
        return None

    small_miss = _pick(lambda r: not r["cache_hit"] and r["model"] == "mock-small")
    large_miss = _pick(lambda r: not r["cache_hit"] and r["model"] == "mock-large")
    cache_hit = _pick(lambda r: r["cache_hit"])

    picked = [small_miss, large_miss, cache_hit]
    if not any(picked):
        return {"skipped": True, "reason": "no requests available for traces"}

    trace_ids = [request["request_id"] for request in picked if request is not None]
    existing = int(
        session.query(TraceEvent).filter(TraceEvent.request_id.in_(trace_ids)).count()
    )
    if existing > 0:
        return {"skipped": True, "reason": f"{existing} trace events already present"}

    added = 0
    for request in picked:
        if request is None:
            continue
        created = request["created_at"]
        is_hit = request["cache_hit"]
        timeline: list[tuple[str, str, int]] = []
        cumulative = 0

        def _push(name: str, status: str, duration: int) -> None:
            nonlocal cumulative
            cumulative += duration
            timeline.append((name, status, duration))  # noqa: B023

        _push("request_received", "success", 2)
        _push("auth_checked", "success", 3)
        _push("rate_limit_checked", "success", 1)
        _push("budget_checked", "success", 2)
        _push("guardrail_checked", "success", 5)
        _push("router_decided", "success", 2)
        _push("cache_checked", "success", 4)
        if is_hit:
            _push("retrieval_completed", "skipped", 0)
            _push("llm_called", "skipped", 0)
            _push("evaluation_completed", "skipped", 0)
        else:
            _push("retrieval_completed", "success", 28)
            _push("llm_called", "success", max(5, request["latency_ms"] - 40))
            _push("evaluation_completed", "success", 4)
        _push("cost_logged", "success", 1)
        _push("response_returned", "success", 1)

        for sequence, (name, status, duration) in enumerate(timeline, start=1):
            session.add(
                TraceEvent(
                    request_id=request["request_id"],
                    sequence=sequence,
                    name=name,
                    status=status,
                    duration_ms=duration,
                    details={
                        "model": request["model"],
                        "cache_hit": is_hit,
                        "router_decision": request["router_decision"],
                    },
                    timestamp=created + timedelta(milliseconds=cumulative),
                )
            )
            added += 1
    session.commit()
    return {"skipped": False, "trace_events": added, "traces": trace_ids}


# ---------------------------------------------------------------------------
# FinOps agent run (completed + verified) and the pending action
# ---------------------------------------------------------------------------


def _seed_agent_data(session: Any) -> dict[str, Any]:
    """Completed FinOps run (verified) + pending action_101 (exact spec shape)."""
    from app.db.models import AgentAction

    if int(session.query(AgentRun).count()) == 0:
        _insert_agent_runs(session)

    if int(session.query(AgentAction).count()) == 0:
        run_b = session.query(AgentRun).filter_by(run_id="run_demo_finops_002").first()
        session.add(
            AgentAction(
                action_id="action_101",
                run_id=run_b.run_id if run_b is not None else None,
                title="Route simple queries to cheaper model",
                description=(
                    "Shift cheap-eligible queries (simple FAQs, cache misses below "
                    "the similarity threshold) from mock-large to mock-small. "
                    "Estimated monthly saving $18.40 at current traffic."
                ),
                expected_monthly_saving_usd=18.4,
                risk_level="low",
                latency_impact="minimal",
                policy_delta={
                    "allowed_models": ["mock-small", "mock-large", "bedrock-cheap"],
                    "require_cache_check": True,
                    "require_evaluation": True,
                },
                approval_required=True,
                status="pending",
            )
        )
        session.commit()
    return _agent_counts(session)


def _cache_stats_from_requests(session: Any) -> dict[str, Any]:
    """Cache stats consistent with the seeded Request rows (tools shape)."""
    from app.db.models import Request

    hits = int(session.query(Request).filter(Request.cache_hit.is_(True)).count())
    misses = int(session.query(Request).filter(Request.cache_hit.is_(False)).count())
    total = hits + misses
    return {
        "hit_count": hits,
        "miss_count": misses,
        "hit_rate": round(hits / total, 4) if total else 0.0,
        "entry_count": 0,
        "source": "requests + cache_entries",
    }


def _usage_metrics_from_requests(session: Any) -> dict[str, Any]:
    """Usage rollup consistent with the seeded rows (tools shape)."""
    from sqlalchemy import func

    from app.db.models import Request, UsageRecord

    total_cost = float(
        session.query(func.coalesce(func.sum(UsageRecord.cost_usd), 0.0)).scalar() or 0.0
    )
    total_input = int(
        session.query(func.coalesce(func.sum(UsageRecord.input_tokens), 0)).scalar() or 0
    )
    total_output = int(
        session.query(func.coalesce(func.sum(UsageRecord.output_tokens), 0)).scalar() or 0
    )
    rows = session.query(Request).all()
    latencies = [row.latency_ms or 0 for row in rows]
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    return {
        "total_requests": len(rows),
        "total_cost_usd": round(total_cost, 6),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "avg_latency_ms": avg_latency,
        "source": "usage_records",
    }


def _insert_agent_runs(session: Any) -> None:
    from app.agents.planner import build_plan
    from app.db.models import AgentStep, AgentToolCall

    try:
        plan = build_plan("finops", "manual") or []
    except Exception:
        plan = [
            {"step": 1, "name": "gather_metrics", "tools": ["get_usage_metrics", "get_cache_stats", "get_model_costs", "get_latency_report"]},
            {"step": 2, "name": "detect_inefficiency"},
            {"step": 3, "name": "generate_hypotheses"},
            {"step": 4, "name": "simulate_policy_changes", "tools": ["simulate_routing_policy", "simulate_cache_threshold"]},
            {"step": 5, "name": "estimate_savings"},
            {"step": 6, "name": "assess_risk"},
            {"step": 7, "name": "create_action_plan"},
            {"step": 8, "name": "request_human_approval"},
            {"step": 9, "name": "apply_local_policy"},
            {"step": 10, "name": "verify_outcome"},
            {"step": 11, "name": "write_audit_event"},
        ]

    usage = _usage_metrics_from_requests(session)
    cache = _cache_stats_from_requests(session)
    now = utcnow()
    yesterday = utcnow() - timedelta(days=1)

    tool_calls = [
        {"tool": "get_usage_metrics", "input": {}, "output": usage, "duration_ms": 12, "status": "success"},
        {"tool": "get_cache_stats", "input": {}, "output": cache, "duration_ms": 9, "status": "success"},
        {
            "tool": "get_model_costs",
            "input": {},
            "output": {
                "model_costs": [
                    {"model": "mock-small", "requests": 240, "cost_usd": 2.31, "input_tokens": 210000, "output_tokens": 110000},
                    {"model": "mock-large", "requests": 160, "cost_usd": 4.18, "input_tokens": 190000, "output_tokens": 95000},
                ],
                "total_cost_usd": round(usage["total_cost_usd"], 6),
            },
            "duration_ms": 8,
            "status": "success",
        },
        {"tool": "get_latency_report", "input": {}, "output": {"avg_ms": usage["avg_latency_ms"], "p95_ms": 612.0, "max_ms": 640.0, "count": usage["total_requests"]}, "duration_ms": 7, "status": "success"},
        {"tool": "simulate_routing_policy", "input": {"model_shift": "cheap", "fraction": 0.3}, "output": {"scenario": "shift_expensive_to_cheap", "fraction": 0.3, "estimated_monthly_saving_usd": 24.5, "assumptions": "mock-large/bedrock-strong -> mock-small/bedrock-cheap at ~25% cost"}, "duration_ms": 11, "status": "success"},
        {"tool": "simulate_cache_threshold", "input": {"threshold": 0.75}, "output": {"current_threshold": 0.82, "proposed_threshold": 0.75, "current_hit_rate": cache["hit_rate"], "estimated_hit_rate": 0.42, "estimated_hit_gain": 0.11, "note": "heuristic estimate; validate on real traffic"}, "duration_ms": 10, "status": "success"},
        {"tool": "estimate_savings", "input": {"routing_saving_usd": 24.5, "cache_saving_usd": 6.2}, "output": {"expected_monthly_saving_usd": 30.7, "routing_saving_usd": 24.5, "cache_saving_usd": 6.2, "confidence": "medium"}, "duration_ms": 6, "status": "success"},
        {
            "tool": "create_action_plan",
            "input": {"title": "Route simple queries to cheaper model", "expected_monthly_saving_usd": 18.4, "risk_level": "low", "latency_impact": "minimal", "approval_required": True, "policy_delta": {"allowed_models": ["mock-small", "mock-large", "bedrock-cheap"], "require_cache_check": True, "require_evaluation": True}},
            "output": {"created": True, "action_id": "action_101", "title": "Route simple queries to cheaper model", "expected_monthly_saving_usd": 18.4, "risk_level": "low", "latency_impact": "minimal", "approval_required": True, "status": "pending"},
            "duration_ms": 14,
            "status": "success",
        },
        {"tool": "request_human_approval", "input": {"action_ids": ["action_101"]}, "output": {"run_id": "run_demo_finops_001", "status": "waiting_approval", "action_ids": ["action_101"]}, "duration_ms": 5, "status": "success"},
        {"tool": "apply_local_policy", "input": {"policy_delta": {"allowed_models": ["mock-small", "mock-large", "bedrock-cheap"], "require_cache_check": True}, "actor": "admin"}, "output": {"applied": True, "policy_version": 2, "policy": {"daily_budget_usd": 2.0}}, "duration_ms": 16, "status": "success"},
        {"tool": "write_audit_event", "input": {"action": "agent.finops.completed", "resource": "run_demo_finops_001", "actor": "finops_agent", "metadata": {"trigger": "manual", "saving_usd": 18.4, "status": "verified"}}, "output": {"written": True, "event_id": "evt_seed_finops_001"}, "duration_ms": 5, "status": "success"},
    ]

    steps = [
        {"name": "gather_metrics", "status": "success", "input": {"trigger": "manual"}, "output": {"usage": usage, "cache": cache}, "duration_ms": 36},
        {"name": "detect_inefficiency", "status": "success", "input": {}, "output": {"findings": [{"type": "repeated_similar_queries", "severity": "low", "detail": "repeated queries eligible for caching"}]}, "duration_ms": 3},
        {"name": "generate_hypotheses", "status": "success", "input": {}, "output": {"hypotheses": ["routing shift", "cache threshold"]}, "duration_ms": 4},
        {"name": "simulate_policy_changes", "status": "success", "input": {"model_shift": "cheap"}, "output": {"routing_saving_usd": 24.5}, "duration_ms": 21},
        {"name": "estimate_savings", "status": "success", "input": {}, "output": {"expected_monthly_saving_usd": 30.7}, "duration_ms": 6},
        {"name": "assess_risk", "status": "success", "input": {}, "output": {"risk_level": "low", "latency_impact": "minimal"}, "duration_ms": 2},
        {"name": "create_action_plan", "status": "success", "input": {}, "output": {"action_id": "action_101"}, "duration_ms": 14},
        {"name": "request_human_approval", "status": "success", "input": {"action_ids": ["action_101"]}, "output": {"status": "waiting_approval"}, "duration_ms": 5},
        {"name": "apply_local_policy", "status": "success", "input": {}, "output": {"policy_version": 2}, "duration_ms": 16},
        {"name": "verify_outcome", "status": "success", "input": {}, "output": {"note": "expected saving confirmed on subsequent requests"}, "duration_ms": 8},
        {"name": "write_audit_event", "status": "success", "input": {}, "output": {"written": True}, "duration_ms": 5},
    ]

    observations = {
        "budget_status": "normal",
        "expensive_model_requests_today": 14,
        "cache_hit_rate": cache["hit_rate"],
        "inefficiencies": [{"type": "repeated_similar_queries", "severity": "low", "detail": "repeated queries eligible for caching"}],
        "hypotheses": ["routing shift", "cache threshold"],
        "simulations": {"routing": {"estimated_monthly_saving_usd": 24.5}, "cache": {"estimated_hit_rate": 0.42}},
    }

    recommendation = {
        "title": "Route simple queries to cheaper model",
        "expected_monthly_saving_usd": 18.4,
        "risk_level": "low",
        "latency_impact": "minimal",
    }

    run_a = AgentRun(
        run_id="run_demo_finops_001",
        agent_type="finops",
        trigger="manual",
        status="verified",
        plan=plan,
        observations=observations,
        recommendation=recommendation,
        approval_status="approved",
        outcome={"note": "policy applied and verified; expected saving confirmed on subsequent requests", "verified_saving_usd": 18.4},
        error=None,
        created_at=yesterday,
        updated_at=now,
    )
    run_b = AgentRun(
        run_id="run_demo_finops_002",
        agent_type="finops",
        trigger="manual",
        status="waiting_approval",
        plan=[{"step": 1, "name": "create_action_plan"}, {"step": 2, "name": "request_human_approval"}],
        observations={},
        recommendation=recommendation,
        approval_status="pending",
        outcome=None,
        error=None,
        created_at=now,
        updated_at=now,
    )
    session.add_all([run_a, run_b])
    session.flush()

    for index, step in enumerate(steps):
        session.add(
            AgentStep(
                run_id="run_demo_finops_001",
                step_index=index + 1,
                name=step["name"],
                status=step["status"],
                input=step.get("input"),
                output=step.get("output"),
                duration_ms=step.get("duration_ms", 0),
                created_at=yesterday,
            )
        )
    for call in tool_calls:
        session.add(
            AgentToolCall(
                run_id="run_demo_finops_001",
                tool=call["tool"],
                input=call.get("input"),
                output=call.get("output"),
                duration_ms=call.get("duration_ms", 0),
                status=call.get("status", "success"),
                created_at=yesterday,
            )
        )
    session.commit()


def _agent_counts(session: Any) -> dict[str, Any]:
    from app.db.models import AgentAction, AgentStep, AgentToolCall

    return {
        "agent_runs": int(session.query(AgentRun).count()),
        "agent_steps": int(session.query(AgentStep).count()),
        "agent_tool_calls": int(session.query(AgentToolCall).count()),
        "agent_actions": int(session.query(AgentAction).count()),
        "pending_action": "action_101",
    }


# ---------------------------------------------------------------------------
# completed eval run (fabricated, deterministic)
# ---------------------------------------------------------------------------


def _seed_eval_run(session: Any) -> dict[str, Any]:
    """One completed eval run with 8-key avg metrics (demo artifact)."""
    from app.db.models import EvalResult, EvalRun

    if int(session.query(EvalRun).count()) > 0:
        return {"skipped": True, "reason": "eval run already present"}

    try:
        from app.eval.runner import load_golden_prompts

        cases = load_golden_prompts()
    except Exception:
        cases = []

    # (relevance, groundedness, safety, completeness, cost_efficiency,
    #  latency_ms, estimated_cost_usd, cacheability, passed)
    fabricated = [
        ("cat_01", 0.90, 1.00, 1.00, 0.95, 0.88, 142, 0.0098, 0.50, True),
        ("cat_02", 0.88, 1.00, 1.00, 0.92, 0.90, 156, 0.0102, 0.50, True),
        ("cat_03", 0.90, 1.00, 1.00, 0.90, 0.87, 138, 0.0095, 0.50, True),
        ("cat_04", 1.00, 1.00, 1.00, 1.00, 1.00, 12, 0.0000, 1.00, True),
        ("cat_05", 0.75, 0.00, 1.00, 0.65, 0.92, 121, 0.0078, 1.00, True),
        ("cat_06", 0.60, 0.00, 1.00, 0.80, 0.70, 512, 0.0412, 1.00, False),
        ("cat_07", 1.00, 1.00, 1.00, 0.90, 0.85, 104, 0.0064, 0.50, True),
        ("cat_08", 1.00, 0.50, 1.00, 1.00, 1.00, 18, 0.0000, 1.00, True),
        ("cat_09", 1.00, 1.00, 1.00, 1.00, 1.00, 9, 0.0000, 1.00, True),
        ("cat_10", 1.00, 1.00, 1.00, 1.00, 0.98, 14, 0.0009, 1.00, True),
    ]

    from app.eval.metrics import average_metrics

    metrics_list: list[dict[str, Any]] = []
    case_by_id = {case["case_id"]: case for case in cases}
    created = (utcnow() - timedelta(days=1)).replace(hour=16, minute=0, second=0, microsecond=0)

    for (
        case_id, relevance, groundedness, safety, completeness, cost_efficiency,
        latency_ms, cost_usd, cacheability, passed,
    ) in fabricated:
        metrics = {
            "relevance": relevance,
            "groundedness": groundedness,
            "safety": safety,
            "completeness": completeness,
            "cost_efficiency": cost_efficiency,
            "latency_ms": latency_ms,
            "estimated_cost_usd": cost_usd,
            "cacheability": cacheability,
        }
        metrics_list.append(metrics)
        source = case_by_id.get(case_id, {})
        session.add(
            EvalResult(
                run_id="eval_demo_seed_001",
                case_id=case_id,
                prompt=str(source.get("prompt", "")),
                expected_behavior=str(source.get("expected_behavior", "")),
                actual_behavior={
                    "router_decision": "REJECT" if case_id in ("cat_04", "cat_09") else ("CACHE_ONLY" if case_id == "cat_10" else "CHEAP_MODEL"),
                    "guardrail_status": "blocked" if case_id in ("cat_04", "cat_09") else "passed",
                    "cache_hit": case_id == "cat_10",
                    "blocked": case_id in ("cat_04", "cat_09"),
                    "model": "mock-small",
                    "provider": "mock",
                    "estimated_cost_usd": cost_usd,
                    "latency_ms": latency_ms,
                    "citations_count": 2 if case_id in ("cat_01", "cat_02", "cat_03", "cat_07", "cat_10") else 0,
                    "answer_preview": "(seeded demo run — see live eval runs for real answers)",
                },
                metrics=metrics,
                passed=passed,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                created_at=created,
            )
        )

    avg = average_metrics(metrics_list)
    passed_count = sum(1 for row in fabricated if row[9])
    session.add(
        EvalRun(
            run_id="eval_demo_seed_001",
            status="completed",
            total_cases=len(fabricated),
            passed_cases=passed_count,
            failed_cases=len(fabricated) - passed_count,
            avg_metrics=avg,
            duration_ms=2450,
            created_at=created,
        )
    )
    session.commit()
    return {
        "skipped": False,
        "run_id": "eval_demo_seed_001",
        "total_cases": len(fabricated),
        "passed_cases": passed_count,
        "failed_cases": len(fabricated) - passed_count,
        "avg_metrics": avg,
    }


# ---------------------------------------------------------------------------
# audit events
# ---------------------------------------------------------------------------


def _seed_audit_events(session: Any, summary: dict[str, Any]) -> int:
    from app.governance.audit import append

    event_ids: list[str] = []
    event_ids.append(
        append(
            actor="system",
            role="system",
            action="demo.seeded",
            resource="demo",
            metadata={
                "documents": summary.get("documents", 0),
                "requests": summary.get("requests", 0),
                "usage_records": summary.get("usage_records", 0),
                "trace_events": summary.get("trace_events", 0),
                "agent_runs": summary.get("agent_runs", 0),
                "agent_actions": summary.get("agent_actions", 0),
                "eval_runs": summary.get("eval_runs", 0),
            },
        ).event_id
    )
    event_ids.append(
        append(
            actor="system",
            role="system",
            action="demo.api_keys.seeded",
            resource="api_key",
            metadata={
                "admin_key_hash_prefix": hash_api_key(DEMO_ADMIN_KEY)[:8],
                "viewer_key_hash_prefix": hash_api_key(DEMO_VIEWER_KEY)[:8],
            },
        ).event_id
    )
    event_ids.append(
        append(
            actor="guardrail_agent",
            role="system",
            action="guardrail.blocked",
            resource="chat",
            metadata={"reason": "restricted_topic", "severity": "high", "source": "demo seed"},
        ).event_id
    )
    event_ids.append(
        append(
            actor="finops_agent",
            role="system",
            action="agent.finops.completed",
            resource="run_demo_finops_001",
            metadata={"trigger": "manual", "saving_usd": 18.4, "status": "verified", "source": "demo seed"},
        ).event_id
    )
    event_ids.append(
        append(
            actor="finops_agent",
            role="system",
            action="agent.action.created",
            resource="action_101",
            metadata={"title": "Route simple queries to cheaper model", "status": "pending", "source": "demo seed"},
        ).event_id
    )
    event_ids.append(
        append(
            actor="eval_runner",
            role="system",
            action="eval.run.seeded",
            resource="eval_demo_seed_001",
            metadata={"total_cases": 10, "source": "demo seed"},
        ).event_id
    )
    return len(event_ids)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> dict[str, Any]:
    """Run the full deterministic demo seed and print a summary."""
    from app.db.models import (
        AgentAction,
        AgentRun,
        ApiKey,
        AuditEvent,
        Document,
        DocumentChunk,
        EvalResult,
        EvalRun,
        Request,
        TraceEvent,
        UsageRecord,
    )

    summary: dict[str, Any] = {}

    init_result = init_db()
    summary["init_db"] = init_result

    with SessionLocal() as session:
        admin_key_id = _ensure_api_key(session, DEMO_ADMIN_KEY, "admin", "admin")
        viewer_key_id = _ensure_api_key(session, DEMO_VIEWER_KEY, "viewer", "viewer")
        if (settings.admin_api_key or "").strip() not in ("", "***"):
            _ensure_api_key(session, settings.admin_api_key.strip(), "admin-env", "admin")
        summary["admin_key_id"] = admin_key_id
        summary["viewer_key_id"] = viewer_key_id

        policy, policy_version = _ensure_policy()
        summary["policy_version"] = policy_version

        summary["ingest"] = _ingest_documents(session)

        usage = _seed_usage_history(session, viewer_key_id)
        summary.update(
            {
                "requests": usage.get("requests", 0),
                "usage_records": usage.get("requests", 0),
                "daily_spend_usd": usage.get("daily_spend_usd", []),
                "requests_by_day": usage.get("requests_by_day", []),
            }
        )

        requests = [
            {
                "request_id": row.request_id,
                "model": row.model,
                "cache_hit": bool(row.cache_hit),
                "latency_ms": row.latency_ms,
                "router_decision": row.router_decision,
                "created_at": row.created_at,
                "estimated_cost_usd": row.estimated_cost_usd,
            }
            for row in session.query(Request).filter(Request.request_id.like("seed_req_%")).all()
        ]
        summary["traces"] = _seed_traces(session, requests)

        summary.update(_seed_agent_data(session))
        summary["eval"] = _seed_eval_run(session)

        counts = {
            "documents": int(session.query(Document).count()),
            "document_chunks": int(session.query(DocumentChunk).count()),
            "api_keys": int(session.query(ApiKey).count()),
            "requests": int(session.query(Request).count()),
            "usage_records": int(session.query(UsageRecord).count()),
            "trace_events": int(session.query(TraceEvent).count()),
            "agent_runs": int(session.query(AgentRun).count()),
            "agent_actions": int(session.query(AgentAction).count()),
            "eval_runs": int(session.query(EvalRun).count()),
            "eval_results": int(session.query(EvalResult).count()),
            "audit_events": int(session.query(AuditEvent).count()),
        }
        summary["counts"] = counts
        summary["audit_events"] = _seed_audit_events(session, counts)

    _print_summary(summary)
    return summary


def _print_summary(summary: dict[str, Any]) -> None:
    """Print seeded counts and the demo API keys (the raw keys are printed ONCE)."""
    line = "=" * 64
    print(line)
    print("Project Prometheus — demo seed complete")
    print(line)

    counts = summary.get("counts", {})
    print(f"documents            : {counts.get('documents', 0)}")
    print(f"document_chunks      : {counts.get('document_chunks', 0)}")
    print(f"api_keys             : {counts.get('api_keys', 0)}")
    print(f"requests             : {counts.get('requests', 0)}")
    print(f"usage_records        : {counts.get('usage_records', 0)}")
    print(f"trace_events         : {counts.get('trace_events', 0)}")
    print(f"agent_runs           : {counts.get('agent_runs', 0)}")
    print(f"agent_steps          : {summary.get('agent_steps', 0)}")
    print(f"agent_tool_calls     : {summary.get('agent_tool_calls', 0)}")
    print(f"agent_actions        : {counts.get('agent_actions', 0)} (action_101 pending)")
    print(f"eval_runs            : {counts.get('eval_runs', 0)}")
    print(f"eval_results         : {counts.get('eval_results', 0)}")
    print(f"audit_events         : {counts.get('audit_events', 0)}")
    daily = summary.get("daily_spend_usd", [])
    if daily:
        print(
            "daily spend (7d)     : "
            + ", ".join(f"${value:.2f}" for value in daily)
            + "  (target ~40-60% of $2.00/day)"
        )
    by_day = summary.get("requests_by_day", [])
    if by_day:
        print("requests per day     : " + ", ".join(str(value) for value in by_day))

    print(line)
    print("DEMO API KEYS (store these; only the hashes are kept at rest):")
    print(f"  admin : {DEMO_ADMIN_KEY}")
    print(f"  viewer: {DEMO_VIEWER_KEY}")
    env_key = (settings.admin_api_key or "").strip()
    if env_key not in ("", "***"):
        print(f"  env ADMIN_API_KEY also active: {env_key}")
    print(line)
    print("Try it: curl -s http://localhost:8000/api/v1/health")
    print("        curl -s -X POST http://localhost:8000/api/v1/chat \\")
    print(f"             -H 'X-API-Key: {DEMO_ADMIN_KEY}' \\")
    print("             -H 'Content-Type: application/json' \\")
    print("             -d '{\"message\": \"What is AI cost governance?\"}'")
    print(line)


if __name__ == "__main__":
    main()
