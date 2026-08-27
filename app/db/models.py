"""SQLAlchemy 2.0 ORM models for Project Prometheus (19 tables).

Conventions:
- UUID-string ids (``request_id`` / ``run_id`` / ``action_id`` / ``event_id``)
  are unique and indexed.
- All timestamps are UTC, stored as ``DateTime(timezone=True)`` with aware
  defaults. SQLite returns naive datetimes on read — use :func:`ensure_utc` /
  :func:`iso_utc` when serializing.
- JSON blobs use SQLAlchemy ``JSON`` (SQLite-backed).
- ``AuditEvent`` is append-only: application code never updates or deletes
  rows (enforced by convention; documented in GOVERNANCE.md).
- ``SseEvent`` is the SSE outbox (B2/D2): id INTEGER PRIMARY KEY AUTOINCREMENT.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime | None) -> datetime | None:
    """Attach UTC tzinfo to naive datetimes (SQLite returns naive on read)."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def iso_utc(value: datetime | None) -> str | None:
    """Serialize a datetime to an ISO-8601 UTC string (naive-safe)."""
    if value is None:
        return None
    return ensure_utc(value).isoformat()


def utc_today() -> str:
    """UTC calendar day as ``YYYY-MM-DD`` (spend-aggregation key)."""
    return utcnow().date().isoformat()


class ApiKey(Base):
    """API keys for MVP auth. Stored as SHA-256 hashes; role: admin | viewer."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="default")
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Request(Base):
    """One chat/agent request through the pipeline (chat response snapshot)."""

    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    api_key_id: Mapped[int | None] = mapped_column(ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    router_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    guardrail_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost_saved_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evaluation_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    response_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class UsageRecord(Base):
    """One cost record per LLM call (and per cache hit, with cost 0 + savings)."""

    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str | None] = mapped_column(
        ForeignKey("requests.request_id", ondelete="SET NULL"), nullable=True, index=True
    )
    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # UTC day YYYY-MM-DD
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="mock")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cache_saved_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class TraceEvent(Base):
    """One step of the per-request trace timeline (12 canonical names)."""

    __tablename__ = "trace_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str | None] = mapped_column(
        ForeignKey("requests.request_id", ondelete="SET NULL"), nullable=True, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="success")
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    details: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class CacheEntry(Base):
    """One semantic-cache entry (answer + embedding + version/TTL gates)."""

    __tablename__ = "cache_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    kb_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cache_version: Mapped[str] = mapped_column(String(16), nullable=False, default="v1")
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Document(Base):
    """Ingested knowledge-base document."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    kb_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class DocumentChunk(Base):
    """Chunk of a document (embeddings live in the vector store, D5)."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=True, index=True
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    details: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class AgentRun(Base):
    """Agent runtime run (finops / reliability / evaluator / guardrail / router)."""

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    agent_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    plan: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    observations: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    recommendation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    approval_status: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    outcome: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class AgentStep(Base):
    """Executed step inside an agent run."""

    __tablename__ = "agent_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.run_id", ondelete="CASCADE"), nullable=True, index=True
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    input: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class AgentToolCall(Base):
    """Logged tool invocation inside an agent run (exact spec shape)."""

    __tablename__ = "agent_tool_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.run_id", ondelete="CASCADE"), nullable=True, index=True
    )
    tool: Mapped[str] = mapped_column(String(128), nullable=False)
    input: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="success")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class AgentAction(Base):
    """FinOps action awaiting (or having received) human approval."""

    __tablename__ = "agent_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.run_id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_monthly_saving_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="low")
    latency_impact: Mapped[str | None] = mapped_column(String(32), nullable=True)
    policy_delta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class Policy(Base):
    """Active policy row; history lives in ``policy_changes`` (version bumps)."""

    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_version: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    body: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class PolicyChange(Base):
    """Append-only policy change log (old/new body, actor, reason)."""

    __tablename__ = "policy_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    old_body: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    new_body: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    actor: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class BudgetAlert(Base):
    """Budget (budget_*) and reliability (reliability_*) alerts — local alert table."""

    __tablename__ = "budget_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class AuditEvent(Base):
    """Append-only audit trail. NEVER update or delete rows (GOVERNANCE.md)."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    role: Mapped[str | None] = mapped_column(String(16), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_id: Mapped[str | None] = mapped_column(
        ForeignKey("requests.request_id", ondelete="SET NULL"), nullable=True, index=True
    )
    details: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class EvalRun(Base):
    """One evaluation-harness run over the golden set."""

    __tablename__ = "eval_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="running")
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class EvalResult(Base):
    """Per-case evaluation result (8 metrics incl. latency/cost/cacheability)."""

    __tablename__ = "eval_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("eval_runs.run_id", ondelete="CASCADE"), nullable=True, index=True
    )
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    expected_behavior: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_behavior: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class FailedRequest(Base):
    """Dead-letter table for failed requests (reliability requirements)."""

    __tablename__ = "failed_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    api_key_id: Mapped[int | None] = mapped_column(ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True)
    error_type: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload_masked: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class SseEvent(Base):
    """SSE outbox row (transactional-outbox pattern, B2/D2)."""

    __tablename__ = "sse_events"
    __table_args__ = {"sqlite_autoincrement": True}  # faithful AUTOINCREMENT on SQLite

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


__all__ = [
    "AgentAction",
    "AgentRun",
    "AgentStep",
    "AgentToolCall",
    "ApiKey",
    "AuditEvent",
    "BudgetAlert",
    "CacheEntry",
    "Document",
    "DocumentChunk",
    "EvalResult",
    "EvalRun",
    "FailedRequest",
    "Policy",
    "PolicyChange",
    "Request",
    "SseEvent",
    "TraceEvent",
    "UsageRecord",
    "ensure_utc",
    "iso_utc",
    "utc_today",
    "utcnow",
]
