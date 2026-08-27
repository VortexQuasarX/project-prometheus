"""GET /api/v1/metrics — dashboard counters."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import require_api_key
from app.observability.metrics_store import get_metrics

router = APIRouter()


@router.get("/metrics")
def metrics(_: object = Depends(require_api_key)) -> dict:
    """Aggregate counters for the dashboard (requests, cost, cache, budget, alerts)."""
    return get_metrics()
