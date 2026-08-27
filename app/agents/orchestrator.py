"""Agent orchestrator: the agent runtime (DECISIONS B16).

Lifecycle: pending -> running -> [waiting_approval -> approved -> applied]
-> verified (or rejected / failed). Statuses are EXACTLY:
pending, running, waiting_approval, approved, rejected, applied, verified,
failed.

``create_run`` executes the agent synchronously via the agent-specific
runner, emits SSE ``agent_started`` / ``agent_completed`` and writes the
``agent.run_created`` audit event. Cross-slice deps (db, governance) are
lazy-imported so this module compiles standalone.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.agents.planner import build_plan
from app.agents.schemas import RunDetail

RUN_STATUSES = ("pending", "running", "waiting_approval", "approved", "rejected", "applied", "verified", "failed")
APPROVAL_STATUSES = ("none", "pending", "approved", "rejected")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _emit_sse(event_type: str, **payload: Any) -> None:
    try:
        from app.core import events  # type: ignore
    except Exception:
        return
    try:
        request_id = payload.pop("request_id", None)
        run_id = payload.pop("run_id", None)
        action_id = payload.pop("action_id", None)
        inner = payload.pop("payload", None)
        body = inner if isinstance(inner, dict) else dict(payload)
        events.emit_sse_event(
            event_type,
            body,
            request_id=request_id if isinstance(request_id, str) else None,
            run_id=run_id if isinstance(run_id, str) else None,
            action_id=action_id if isinstance(action_id, str) else None,
        )
    except Exception:
        return


def _new_session() -> Any:
    """Open a DB session from app.db.session (interface-adaptive)."""
    try:
        from app.db import session as _session_mod
    except Exception as exc:  # pragma: no cover - runtime only
        raise RuntimeError("app.db.session is not importable") from exc

    for factory_name in ("SessionLocal", "session_factory", "get_db"):
        factory = getattr(_session_mod, factory_name, None)
        if factory is None:
            continue
        try:
            result = factory()
            if hasattr(result, "__next__"):  # generator-style get_db()
                return next(result)
            if hasattr(result, "query") or hasattr(result, "execute"):
                return result
        except Exception:
            continue
    raise RuntimeError("no usable session factory found in app.db.session")


def _models() -> Any:
    from app.db import models  # lazy: cross-slice dependency

    return models


def _set(run: Any, name: str, value: Any) -> None:
    if hasattr(run, name):
        try:
            setattr(run, name, value)
        except Exception:
            pass


def _serialize_run(run: Any) -> dict[str, Any]:
    def _get(name: str, default: Any = None) -> Any:
        try:
            value = getattr(run, name, default)
        except Exception:
            return default
        if value is None:
            return default
        return value

    def _iso(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return value.isoformat()
        except Exception:
            return str(value)

    return {
        "run_id": _get("run_id"),
        "agent_type": _get("agent_type"),
        "trigger": _get("trigger"),
        "status": _get("status", "pending"),
        "plan": _get("plan", []),
        "steps": _get("steps", []),
        "tool_calls": _get("tool_calls", []),
        "observations": _get("observations", {}),
        "recommendation": _get("recommendation"),
        "approval_status": _get("approval_status", "none"),
        "outcome": _get("outcome"),
        "created_at": _iso(_get("created_at")),
        "updated_at": _iso(_get("updated_at")),
    }


def _expected_saving(run: Any) -> float:
    try:
        rec = getattr(run, "recommendation", None) or {}
        if isinstance(rec, dict):
            value = rec.get("expected_monthly_saving_usd", 0.0)
            return float(value or 0.0)
    except Exception:
        pass
    return 0.0


# ---------------------------------------------------------------------------
# Agent-specific runners for the non-FinOps agents
# ---------------------------------------------------------------------------


def _run_guardrail(run: Any, params: dict[str, Any] | None, db: Any) -> None:
    from app.agents.guardrail_agent import check
    from app.governance.policy_engine import get_policy

    params = params or {}
    policy, _ = get_policy()
    query = str(params.get("query", ""))
    result = check(query, policy=policy, estimated_request_cost=params.get("estimated_request_cost"))
    _set(run, "observations", {"query": query, "blocked": result.blocked, "reasons": result.reasons, "pii_found": result.pii_found})
    _set(
        run,
        "recommendation",
        {"decision": "REJECT" if result.blocked else "PASS", "risk_level": result.risk_level, "reasons": result.reasons},
    )
    _set(run, "status", "verified")
    _set(run, "outcome", {"blocked": result.blocked, "masked": result.masked_text is not None})


def _run_router(run: Any, params: dict[str, Any] | None, db: Any) -> None:
    from app.agents.router_agent import decide
    from app.governance.policy_engine import get_policy

    params = params or {}
    policy, _ = get_policy()
    decision = decide(
        str(params.get("query", "")),
        budget_status=str(params.get("budget_status", "normal")),
        policy=policy,
        cache_similarity=params.get("cache_similarity"),
        guardrail_risk=str(params.get("guardrail_risk", "low")),
        query_category=params.get("query_category"),
    )
    _set(run, "observations", {"query": params.get("query", ""), "inputs": {k: v for k, v in params.items() if k != "query"}})
    _set(run, "recommendation", decision.to_dict())
    _set(run, "status", "verified")
    _set(run, "outcome", {"decision": decision.decision, "model": decision.model})


def _run_evaluator(run: Any, params: dict[str, Any] | None, db: Any) -> None:
    from app.agents.evaluator_agent import evaluate
    from app.governance.policy_engine import get_policy

    params = params or {}
    policy, _ = get_policy()
    result = evaluate(
        request_id=str(params.get("request_id", run.run_id)),
        query=str(params.get("query", "")),
        answer=str(params.get("answer", "")),
        citations=params.get("citations") or [],
        cost_usd=float(params.get("cost_usd", 0.0)),
        model=str(params.get("model", "")),
        router_decision=str(params.get("router_decision", "")),
        input_tokens=int(params.get("input_tokens", 0)),
        output_tokens=int(params.get("output_tokens", 0)),
        policy=policy,
    )
    _set(run, "observations", {"request_id": params.get("request_id"), "scores": result.to_dict()})
    _set(run, "recommendation", result.to_dict())
    _set(run, "status", "verified")
    _set(run, "outcome", {"passed": result.passed, "overall_score": result.overall_score, "feedback": result.feedback})


_RUNNERS: dict[str, Any] = {
    "finops": None,  # set below to avoid circular import at module load
    "reliability": None,
    "guardrail": _run_guardrail,
    "router": _run_router,
    "evaluator": _run_evaluator,
}


def _resolve_runner(agent_type: str) -> Any:
    if agent_type == "finops":
        if _RUNNERS["finops"] is None:
            from app.agents.finops_agent import run_finops

            _RUNNERS["finops"] = run_finops
        return _RUNNERS["finops"]
    if agent_type == "reliability":
        if _RUNNERS["reliability"] is None:
            from app.agents.reliability_agent import run_reliability

            _RUNNERS["reliability"] = run_reliability
        return _RUNNERS["reliability"]
    return _RUNNERS[agent_type]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_run(agent_type: str, trigger: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create and synchronously execute an agent run. Returns RunDetail dict."""
    if agent_type not in _RUNNERS:
        raise ValueError(f"unknown agent_type: {agent_type}")

    db = _new_session()
    run = None
    try:
        models = _models()
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        run = models.AgentRun(
            run_id=run_id,
            agent_type=agent_type,
            trigger=trigger,
            status="pending",
            plan=build_plan(agent_type, trigger),
            observations={},
            recommendation=None,
            approval_status="none",
            outcome=None,
            error=None,
            created_at=now,
            updated_at=now,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        _emit_sse("agent_started", run_id=run_id, payload={"agent_type": agent_type, "trigger": trigger})
        try:
            from app.governance.audit import append

            append(
                actor="system",
                role="system",
                action="agent.run_created",
                resource=run_id,
                metadata={"agent_type": agent_type, "trigger": trigger},
            )
        except Exception:
            pass

        _set(run, "status", "running")
        _set(run, "updated_at", datetime.now(UTC))
        db.commit()

        runner = _resolve_runner(agent_type)
        runner(run, params or {}, db)

        final_status = getattr(run, "status", "verified")
        _set(run, "updated_at", datetime.now(UTC))
        db.commit()
        _emit_sse("agent_completed", run_id=run_id, payload={"agent_type": agent_type, "status": final_status})
        return _serialize_run(run)
    except Exception as exc:  # noqa: BLE001
        if run is not None:
            try:
                _set(run, "status", "failed")
                _set(run, "outcome", {"error": f"{type(exc).__name__}: {exc}"})
                _set(run, "updated_at", datetime.now(UTC))
                db.commit()
                _emit_sse("agent_completed", run_id=getattr(run, "run_id", ""), payload={"status": "failed"})
                return _serialize_run(run)
            except Exception:
                db.rollback()
        raise
    finally:
        try:
            db.close()
        except Exception:
            pass


def list_runs(
    status: str | None = None,
    agent_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Return ``{items: [...RunSummary], total}``."""
    db = _new_session()
    try:
        models = _models()
        query = db.query(models.AgentRun)
        if status:
            query = query.filter(models.AgentRun.status == status)
        if agent_type:
            query = query.filter(models.AgentRun.agent_type == agent_type)
        total = query.count()
        rows = query.order_by(getattr(models.AgentRun, "created_at", models.AgentRun.id).desc()).offset(offset).limit(limit).all()
        items = []
        for run in rows:
            d = _serialize_run(run)
            items.append(
                {
                    "run_id": d["run_id"],
                    "agent_type": d["agent_type"],
                    "trigger": d["trigger"],
                    "status": d["status"],
                    "recommendation": d["recommendation"],
                    "expected_saving_usd": _expected_saving(run),
                    "created_at": d["created_at"],
                    "updated_at": d["updated_at"],
                }
            )
        return {"items": items, "total": total}
    finally:
        try:
            db.close()
        except Exception:
            pass


def get_run(run_id: str) -> dict[str, Any]:
    """Return the full RunDetail dict; raises KeyError if unknown."""
    db = _new_session()
    try:
        models = _models()
        run = db.query(models.AgentRun).filter(models.AgentRun.run_id == run_id).first()
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        detail = _serialize_run(run)
        steps = (
            db.query(models.AgentStep)
            .filter(models.AgentStep.run_id == run_id)
            .order_by(models.AgentStep.step_index.asc(), models.AgentStep.id.asc())
            .all()
        )
        tool_calls = (
            db.query(models.AgentToolCall)
            .filter(models.AgentToolCall.run_id == run_id)
            .order_by(models.AgentToolCall.id.asc())
            .all()
        )
        detail["steps"] = [
            {
                "name": getattr(s, "name", ""),
                "status": getattr(s, "status", ""),
                "input": getattr(s, "input", {}) or {},
                "output": getattr(s, "output", {}) or {},
                "duration_ms": int(getattr(s, "duration_ms", 0) or 0),
            }
            for s in steps
        ]
        detail["tool_calls"] = [
            {
                "tool": getattr(t, "tool", ""),
                "input": getattr(t, "input", {}) or {},
                "output": getattr(t, "output", {}) or {},
                "duration_ms": int(getattr(t, "duration_ms", 0) or 0),
                "status": getattr(t, "status", ""),
            }
            for t in tool_calls
        ]
        return detail
    finally:
        try:
            db.close()
        except Exception:
            pass


def to_run_detail(run_data: dict[str, Any]) -> RunDetail:
    """Validate a serialized run dict against the RunDetail schema."""
    return RunDetail(**run_data)


__all__ = ["create_run", "list_runs", "get_run", "RUN_STATUSES", "APPROVAL_STATUSES", "to_run_detail"]
