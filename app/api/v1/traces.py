"""GET /api/v1/traces + /api/v1/traces/{request_id} — observability."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.errors import PrometheusError
from app.core.security import require_api_key
from app.observability.trace_store import get_timeline, get_trace_summary, list_traces

router = APIRouter()


@router.get("/traces")
def traces(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: str | None = None,
    _: object = Depends(require_api_key),
) -> dict:
    """Trace summaries, newest first."""
    return list_traces(limit=limit, offset=offset, status=status)


@router.get("/traces/{request_id}")
def trace_detail(
    request_id: str,
    _: object = Depends(require_api_key),
) -> dict:
    """Full event timeline for one request."""
    summary = get_trace_summary(request_id)
    if summary is None:
        raise PrometheusError(
            f"Unknown request_id: {request_id}",
            code="not_found",
            status_code=404,
        )
    return {
        "request_id": request_id,
        "status": summary.get("status", "completed"),
        "created_at": summary.get("created_at"),
        "timeline": get_timeline(request_id),
        "summary": summary,
    }
