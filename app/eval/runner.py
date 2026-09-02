"""Evaluation runner (app/eval/runner.py).

Runs the golden catalogue from ``evals/golden_prompts.yaml`` through the
chat **service layer in-process** (DECISIONS B17 / subagent_01 D10 — the same
pipeline the API uses, with a synthetic request per case; no HTTP recursion,
so eval runs are deterministic and work without a running server).

Flow per case:

1. resolve an admin API key (env ``ADMIN_API_KEY`` if usable, else a seeded
   ``prometheus-eval-admin-key`` row) — hashed at rest;
2. call ``run_chat_pipeline`` from ``app.api.v1.chat`` (lazy import) with a
   synthetic ``request_id`` ``eval_<run_id>_<case_id>``;
3. judge the response with :func:`app.eval.judge.judge_case`;
4. persist an ``eval_results`` row; aggregate ``avg_metrics`` (8 SPEC keys);
5. persist an ``eval_runs`` row.

The ``repeated cacheable question`` category is executed **twice** (miss then
hit) and judged on the second response, exercising the semantic cache.

The chat API slice is not required to exist when this module is imported —
``app.api.v1.chat`` is imported lazily inside :func:`run_evals`.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

import yaml

from app.core.config import settings
from app.core.security import hash_api_key
from app.eval.judge import judge_case
from app.eval.metrics import average_metrics

EVALS_DIR = Path(__file__).resolve().parents[2] / "evals"

REQUIRED_CASE_FIELDS = (
    "case_id",
    "category",
    "prompt",
    "expected_behavior",
    "expect_blocked",
    "cacheable",
)

#: Category executed twice (first call = cache miss, second = cache hit).
REPEATED_CACHEABLE_CATEGORY = "repeated cacheable question"


# ---------------------------------------------------------------------------
# golden catalogue loading
# ---------------------------------------------------------------------------


def load_golden_prompts() -> list[dict[str, Any]]:
    """Load and validate ``evals/golden_prompts.yaml`` (raises on bad input)."""
    path = EVALS_DIR / "golden_prompts.yaml"
    if not path.exists():
        raise FileNotFoundError(f"golden prompts not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw_cases = data.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError(f"golden_prompts.yaml must contain a non-empty 'cases' list ({path})")

    cases: list[dict[str, Any]] = []
    for raw in raw_cases:
        case = {str(key): value for key, value in dict(raw).items()}
        missing = [field for field in REQUIRED_CASE_FIELDS if field not in case]
        if missing:
            raise ValueError(f"golden case missing required fields {missing}: {case}")
        case["case_id"] = str(case["case_id"])
        case["category"] = str(case["category"])
        case["prompt"] = str(case["prompt"])
        case["expected_behavior"] = str(case["expected_behavior"])
        case["expect_blocked"] = bool(case["expect_blocked"])
        case["cacheable"] = bool(case["cacheable"])
        cases.append(case)
    return cases


def load_expected_behaviors() -> dict[str, Any]:
    """Load ``evals/expected_behaviors.yaml`` (category -> behavior + pass_rule)."""
    path = EVALS_DIR / "expected_behaviors.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return dict(data.get("categories") or {})


# ---------------------------------------------------------------------------
# chat service-layer bridge (lazy; chat slice may not exist yet)
# ---------------------------------------------------------------------------


def _call_chat_pipeline(prompt: str, api_key: str, request_id: str) -> Any:
    """Call ``app.api.v1.chat.run_chat_pipeline`` with adaptive signature.

    The chat slice owns the authoritative signature; this bridge probes the
    most likely shapes (``query``/``message`` keyword, positional) and raises
    a descriptive ``TypeError`` when none match.
    """
    try:
        from app.api.v1.chat import run_chat_pipeline
    except Exception as exc:  # pragma: no cover - chat slice not built yet
        raise RuntimeError(
            "app.api.v1.chat.run_chat_pipeline is not importable; the chat "
            "service slice must exist before eval runs can execute"
        ) from exc

    candidates = (
        lambda: run_chat_pipeline(query=prompt, api_key=api_key, request_id=request_id),
        lambda: run_chat_pipeline(message=prompt, api_key=api_key, request_id=request_id),
        lambda: run_chat_pipeline(
            query=prompt, api_key=api_key, request_id=request_id, metadata={"source": "eval"}
        ),
        lambda: run_chat_pipeline(prompt, api_key, request_id),
    )
    last_error: BaseException | None = None
    for candidate in candidates:
        try:
            return candidate()
        except TypeError as exc:
            last_error = exc
            continue
        except Exception:
            raise  # non-signature failures propagate to the case handler
    raise TypeError(
        "run_chat_pipeline signature mismatch: expected (query|message, api_key, "
        f"request_id) keyword or positional call; last probe error: {last_error}"
    )


def _raise_on_error_envelope(response: Any) -> None:
    """Surface error-envelope responses instead of silently failing the case."""
    if not isinstance(response, dict):
        return
    if "answer" in response:
        return
    if "error" in response:
        error = response["error"]
        detail = error.get("message", error) if isinstance(error, dict) else error
        raise RuntimeError(f"chat pipeline returned an error envelope: {detail}")


# ---------------------------------------------------------------------------
# admin key resolution
# ---------------------------------------------------------------------------


def _resolve_admin_key(session: Any) -> str:
    """Return a raw admin API key, ensuring its hash row exists (at rest)."""
    from app.db.models import ApiKey

    candidate = (settings.admin_api_key or "").strip()
    if candidate and candidate != "***":
        raw = candidate
    else:
        raw = "prometheus-eval-admin-key"

    existing = session.query(ApiKey).filter_by(key_hash=hash_api_key(raw)).first()
    if existing is None:
        session.add(
            ApiKey(key_hash=hash_api_key(raw), name="eval-runner", role="admin", is_active=True)
        )
        session.commit()
    elif not existing.is_active:
        existing.is_active = True
        session.commit()
    return raw


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


def run_evals(limit: int | None = None, golden_set: str | None = None, organization_id: str | None = None, db: Any = None) -> dict[str, Any]:
    """Execute the golden set through the chat pipeline and persist the run.

    ``limit``       — run at most the first N cases.
    ``golden_set``  — filter by exact ``category`` or ``case_id``.
    ``db``          — optional SQLAlchemy session (own session opened when None).

    Returns ``{run_id, status, total_cases, passed_cases, failed_cases,
    avg_metrics, duration_ms}``.
    """
    cases = load_golden_prompts()
    if golden_set:
        cases = [
            case
            for case in cases
            if case["category"] == golden_set or case["case_id"] == golden_set
        ]
        if not cases:
            raise ValueError(f"golden_set {golden_set!r} matched no cases")
    if limit is not None:
        cases = cases[: max(0, int(limit))]
    if not cases:
        raise ValueError("no golden cases to run")

    run_id = f"eval_{uuid.uuid4().hex[:12]}"
    started = time.perf_counter()
    session, owns_session = _open_session(db)
    try:
        api_key = _resolve_admin_key(session)
        results: list[dict[str, Any]] = []
        for case in cases:
            case_id = case["case_id"]
            try:
                if case["category"] == REPEATED_CACHEABLE_CATEGORY:
                    _call_chat_pipeline(case["prompt"], api_key, f"{run_id}_{case_id}")
                    response = _call_chat_pipeline(
                        case["prompt"], api_key, f"{run_id}_{case_id}_r2"
                    )
                else:
                    response = _call_chat_pipeline(case["prompt"], api_key, f"{run_id}_{case_id}")
                _raise_on_error_envelope(response)
                verdict = judge_case(case, response, db=session)
            except Exception as exc:  # noqa: BLE001 - one bad case must not kill the run
                verdict = _failure_verdict(case, exc)
            results.append(verdict)
        duration_ms = int((time.perf_counter() - started) * 1000)
        return _persist_run(session, run_id, cases, results, duration_ms)
    finally:
        if owns_session:
            session.close()


def list_eval_runs(limit: int = 50, offset: int = 0, organization_id: str | None = None, db: Any = None) -> dict[str, Any]:
    """Eval-run summaries, newest first: ``{"items": [...], "total": n}``."""
    from app.db.models import EvalRun, iso_utc

    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    session, owns_session = _open_session(db)
    try:
        total = int(session.query(EvalRun).count())
        rows = (
            session.query(EvalRun)
            .order_by(EvalRun.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        items = [
            {
                "run_id": row.run_id,
                "status": row.status,
                "total_cases": row.total_cases,
                "passed_cases": row.passed_cases,
                "failed_cases": row.failed_cases,
                "avg_metrics": dict(row.avg_metrics or {}),
                "duration_ms": row.duration_ms,
                "created_at": iso_utc(row.created_at),
            }
            for row in rows
        ]
        return {"items": items, "total": total}
    finally:
        if owns_session:
            session.close()


def get_eval_run(run_id: str, db: Any = None) -> dict[str, Any]:
    """Full eval run with per-case results; raises ``KeyError`` when unknown."""
    from app.db.models import EvalResult, EvalRun, iso_utc

    session, owns_session = _open_session(db)
    try:
        run = session.query(EvalRun).filter_by(run_id=run_id).first()
        if run is None:
            raise KeyError(f"eval run not found: {run_id}")
        result_rows = (
            session.query(EvalResult)
            .filter_by(run_id=run_id)
            .order_by(EvalResult.id.asc())
            .all()
        )
        cases = [
            {
                "case_id": row.case_id,
                "prompt": row.prompt,
                "passed": bool(row.passed),
                "metrics": dict(row.metrics or {}),
                "latency_ms": row.latency_ms,
                "cost_usd": row.cost_usd,
            }
            for row in result_rows
        ]
        return {
            "run_id": run.run_id,
            "status": run.status,
            "total_cases": run.total_cases,
            "passed_cases": run.passed_cases,
            "failed_cases": run.failed_cases,
            "avg_metrics": dict(run.avg_metrics or {}),
            "duration_ms": run.duration_ms,
            "cases": cases,
            "created_at": iso_utc(run.created_at),
        }
    finally:
        if owns_session:
            session.close()


def _failure_verdict(case: dict[str, Any], exc: BaseException) -> dict[str, Any]:
    """Zero-score verdict for a case whose pipeline call raised."""
    error_text = f"{type(exc).__name__}: {exc}"
    metrics = {
        "relevance": 0.0,
        "groundedness": 0.0,
        "safety": 0.0,
        "completeness": 0.0,
        "cost_efficiency": 0.0,
        "latency_ms": 0,
        "estimated_cost_usd": 0.0,
        "cacheability": 0.0,
    }
    return {
        "case_id": case["case_id"],
        "metrics": metrics,
        "overall": 0.0,
        "passed": False,
        "feedback": [f"pipeline call failed: {error_text}"],
        "expected_behavior": case.get("expected_behavior", ""),
        "actual_behavior": {"error": error_text},
    }


# ---------------------------------------------------------------------------
# persistence helpers
# ---------------------------------------------------------------------------


def _open_session(db: Any = None) -> tuple[Any, bool]:
    if db is not None:
        return db, False
    from app.db.session import SessionLocal

    return SessionLocal(), True


def _persist_run(
    session: Any,
    run_id: str,
    cases: list[dict[str, Any]],
    verdicts: list[dict[str, Any]],
    duration_ms: int,
) -> dict[str, Any]:
    from app.db.models import EvalResult, EvalRun

    metrics_list = [verdict["metrics"] for verdict in verdicts]
    passed = [verdict["passed"] for verdict in verdicts]
    total = len(verdicts)
    passed_count = sum(1 for value in passed if value)
    failed_count = total - passed_count
    avg = average_metrics(metrics_list)

    for case, verdict in zip(cases, verdicts, strict=False):
        session.add(
            EvalResult(
                run_id=run_id,
                case_id=verdict["case_id"],
                prompt=case["prompt"],
                expected_behavior=verdict["expected_behavior"],
                actual_behavior=verdict["actual_behavior"],
                metrics=verdict["metrics"],
                passed=bool(verdict["passed"]),
                latency_ms=int(verdict["metrics"].get("latency_ms", 0) or 0),
                cost_usd=float(verdict["metrics"].get("estimated_cost_usd", 0.0) or 0.0),
            )
        )

    session.add(
        EvalRun(
            run_id=run_id,
            status="completed",
            total_cases=total,
            passed_cases=passed_count,
            failed_cases=failed_count,
            avg_metrics=avg,
            duration_ms=duration_ms,
        )
    )
    session.commit()

    return {
        "run_id": run_id,
        "status": "completed",
        "total_cases": total,
        "passed_cases": passed_count,
        "failed_cases": failed_count,
        "avg_metrics": avg,
        "duration_ms": duration_ms,
    }


__all__ = [
    "EVALS_DIR",
    "load_golden_prompts",
    "load_expected_behaviors",
    "run_evals",
    "list_eval_runs",
    "get_eval_run",
    "_call_chat_pipeline",
    "_resolve_admin_key",
]
