"""GET /api/v1/events/stream — SSE live events (transactional-outbox poller).

Replays the last 10 minutes of outbox rows on connect, then polls for new rows
every 400ms. Keepalive comment frames every 15s keep proxies from timing out.

Auth note: browsers' EventSource cannot set the X-API-Key header, so a
``?api_key=`` query parameter is accepted ONLY when ``APP_ENV=local``
(documentdev escape hatch, DECISIONS D9).
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.config import settings
from app.core.errors import PrometheusError
from app.core.events import recent_sse_events
from app.core.security import hash_api_key
from app.db.models import ApiKey
from app.db.session import SessionLocal

router = APIRouter()

REPLAY_WINDOW_MINUTES = 10
POLL_INTERVAL_S = 0.4
KEEPALIVE_INTERVAL_S = 15.0


def _authorize(request: Request, x_api_key: str | None, api_key: str | None) -> None:
    raw = x_api_key or (api_key if settings.app_env == "local" else None)
    if not raw:
        raise PrometheusError("Missing API key", code="missing_api_key", status_code=401)
    with SessionLocal() as session:
        row = session.scalar(select(ApiKey).where(ApiKey.key_hash == hash_api_key(raw)))
    if row is None or not row.is_active:
        raise PrometheusError("Invalid API key", code="invalid_api_key", status_code=401)


def _frame(event_type: str, payload: dict) -> str:
    data = json.dumps({"event": event_type, "data": payload}, ensure_ascii=False)
    return f"event: {event_type}\ndata: {data}\n\n"


@router.get("/events/stream")
async def event_stream(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    api_key: str | None = Query(default=None),
):
    _authorize(request, x_api_key, api_key)

    async def gen():
        watermark = 0
        cutoff = datetime.now(UTC) - timedelta(minutes=REPLAY_WINDOW_MINUTES)
        last_keepalive = datetime.now(UTC)
        try:
            for ev in recent_sse_events(since_id=0, limit=200):
                created = ev.get("created_at") or ""
                if created and created >= cutoff.isoformat():
                    yield _frame(ev.get("event_type", "message"), ev.get("payload") or {})
                watermark = max(watermark, int(ev.get("id") or 0))
            while True:
                for ev in recent_sse_events(since_id=watermark, limit=50):
                    yield _frame(ev.get("event_type", "message"), ev.get("payload") or {})
                    watermark = max(watermark, int(ev.get("id") or 0))
                now = datetime.now(UTC)
                if (now - last_keepalive).total_seconds() >= KEEPALIVE_INTERVAL_S:
                    yield ": ping\n\n"
                    last_keepalive = now
                await asyncio.sleep(POLL_INTERVAL_S)
        except asyncio.CancelledError:  # client disconnect
            return

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
