"""GET /api/v1/traces + /api/v1/traces/{request_id} — observability."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.errors import PrometheusError
from app.core.rbac import require_permission
from app.observability.trace_store import get_timeline, get_trace_summary, list_traces

router = APIRouter()


@router.get("/traces")
def traces(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: str | None = None,
    key: object = Depends(require_permission("traces:read")),
) -> dict:
    """Trace summaries, newest first (org-scoped)."""
    return list_traces(limit=limit, offset=offset, status=status, organization_id=getattr(key, "organization_id", None))


@router.get("/traces/{request_id}")
def trace_detail(
    request_id: str,
    key: object = Depends(require_permission("traces:read")),
) -> dict:
    """Full event timeline for one request."""
    summary = get_trace_summary(
        request_id, organization_id=getattr(key, "organization_id", None)
    )
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
