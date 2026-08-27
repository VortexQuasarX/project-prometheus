"""Trace events: append-only per-request timeline + trace list queries.

Trace events use the 12 canonical names from SPEC.md; each row carries
request_id, sequence, name, status, duration_ms, metadata, timestamp.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from app.core.logging import get_logger
from app.db.models import Request, TraceEvent, iso_utc
from app.db.session import SessionLocal

logger = get_logger("prometheus.traces")

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

TRACE_EVENT_NAME_SET: frozenset[str] = frozenset(TRACE_EVENT_NAMES)


def add_trace_event(
    request_id: str,
    name: str,
    status: str = "success",
    duration_ms: int = 0,
    metadata: dict[str, Any] | None = None,
) -> TraceEvent:
    """Append a trace event (sequence auto-increments per request)."""
    if name not in TRACE_EVENT_NAME_SET:
        logger.warning("Trace event name %r is not canonical (SPEC.md)", name)
    with SessionLocal() as session:
        last = session.scalar(
            select(func.max(TraceEvent.sequence)).where(TraceEvent.request_id == request_id)
        )
        event = TraceEvent(
            request_id=request_id,
            sequence=int(last or 0) + 1,
            name=name,
            status=status,
            duration_ms=int(duration_ms or 0),
            details=metadata or {},
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return event


def get_timeline(request_id: str) -> list[dict[str, Any]]:
    """Full event timeline for one request, ordered by sequence."""
    with SessionLocal() as session:
        rows = session.scalars(
            select(TraceEvent)
            .where(TraceEvent.request_id == request_id)
            .order_by(TraceEvent.sequence.asc())
        ).all()
        return [
            {
                "request_id": row.request_id,
                "sequence": row.sequence,
                "name": row.name,
                "status": row.status,
                "duration_ms": row.duration_ms,
                "metadata": row.details or {},
                "timestamp": iso_utc(row.timestamp),
            }
            for row in rows
        ]


def get_trace_summary(request_id: str) -> dict[str, Any] | None:
    """Request-level summary for the trace-detail endpoint (None -> 404)."""
    with SessionLocal() as session:
        row = session.scalar(select(Request).where(Request.request_id == request_id))
        if row is None:
            return None
        return {
            "request_id": row.request_id,
            "status": row.status,
            "model": row.model,
            "provider": row.provider,
            "router_decision": row.router_decision,
            "cache_hit": row.cache_hit,
            "cost_usd": row.estimated_cost_usd or 0.0,
            "cost_saved_usd": row.cost_saved_usd or 0.0,
            "latency_ms": row.latency_ms,
            "guardrail_status": row.guardrail_status,
            "evaluation_score": row.evaluation_score,
            "created_at": iso_utc(row.created_at),
        }


def list_traces(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
) -> dict[str, Any]:
    """Trace summaries, newest first: ``{"items": [...], "total": n}``."""
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    with SessionLocal() as session:
        count_query = select(func.count(Request.id))
        query = select(Request)
        if status:
            query = query.where(Request.status == status)
            count_query = count_query.where(Request.status == status)
        total = int(session.scalar(count_query) or 0)
        rows = session.scalars(
            query.order_by(Request.created_at.desc()).offset(offset).limit(limit)
        ).all()
        items = [
            {
                "request_id": row.request_id,
                "status": row.status,
                "model": row.model,
                "provider": row.provider,
                "router_decision": row.router_decision,
                "cache_hit": row.cache_hit,
                "cost_usd": row.estimated_cost_usd or 0.0,
                "latency_ms": row.latency_ms,
                "created_at": iso_utc(row.created_at),
            }
            for row in rows
        ]
        return {"items": items, "total": total}
