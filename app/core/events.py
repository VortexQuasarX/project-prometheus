"""SSE outbox: canonical event types + append-only ``sse_events`` writer.

The streaming endpoint slice polls the outbox via :func:`recent_sse_events`;
producers (chat pipeline, orchestrator, budget service, approvals) call
:func:`emit_sse_event`. This is the transactional-outbox pattern: SSE events
survive restarts and can be replayed after a client reconnect (B2/D2).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models import SseEvent, iso_utc
from app.db.session import SessionLocal

logger = get_logger("prometheus.sse")

SSE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "request_started",
        "agent_started",
        "agent_completed",
        "budget_warning",
        "action_pending_approval",
        "action_approved",
        "action_applied",
    }
)


def emit_sse_event(
    event_type: str,
    payload: dict[str, Any],
    *,
    request_id: str | None = None,
    run_id: str | None = None,
    action_id: str | None = None,
) -> SseEvent:
    """Append one row to the SSE outbox (own short-lived session) and log it."""
    if event_type not in SSE_EVENT_TYPES:
        logger.warning("SSE event type not in canonical set: %s", event_type)
    if not isinstance(payload, dict):
        logger.warning("SSE payload is not a dict; wrapping it")
        payload = {"value": payload}
    with SessionLocal() as session:
        event = SseEvent(
            event_type=event_type,
            request_id=request_id,
            run_id=run_id,
            action_id=action_id,
            payload=payload,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
    logger.info(
        "sse event emitted",
        extra={
            "event": event_type,
            "request_id": request_id,
            "run_id": run_id,
            "action_id": action_id,
            "sse_id": event.id,
        },
    )
    return event


def recent_sse_events(since_id: int = 0, limit: int = 200) -> list[dict[str, Any]]:
    """Return outbox rows with ``id > since_id`` ascending (replay support)."""
    with SessionLocal() as session:
        rows = session.scalars(
            select(SseEvent)
            .where(SseEvent.id > int(since_id))
            .order_by(SseEvent.id.asc())
            .limit(max(1, min(int(limit), 1000)))
        ).all()
        return [
            {
                "id": row.id,
                "event_type": row.event_type,
                "request_id": row.request_id,
                "run_id": row.run_id,
                "action_id": row.action_id,
                "payload": row.payload or {},
                "created_at": iso_utc(row.created_at),
            }
            for row in rows
        ]
