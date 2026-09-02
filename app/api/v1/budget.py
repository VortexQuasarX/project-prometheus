"""GET /api/v1/budget + POST /api/v1/budget/kill-switch â€” FinOps control."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.errors import PrometheusError
from app.core.rbac import require_permission
from app.governance.budget import get_alerts, get_budget_status
from app.governance.kill_switch import KILL_SWITCH_MODES, set_mode

router = APIRouter()


class KillSwitchRequest(BaseModel):
    kill_switch_mode: str = Field(..., pattern="^(off|cache_only|cheap_only|block_all)$")
    reason: str | None = Field(default=None, max_length=500)


@router.get("/budget")
def budget(_: object = Depends(require_permission("budget:read"))) -> dict:
    """Daily/monthly spend, budget state, kill-switch mode, recommendations."""
    return get_budget_status()


@router.get("/alerts")
def alerts(
    limit: int = Query(20, ge=1, le=100),
    _: object = Depends(require_permission("budget:read")),
) -> dict:
    """Recent budget/reliability alerts (spec-gap fix endpoint)."""
    return {"items": get_alerts(limit=limit)}


@router.post("/budget/kill-switch")
def kill_switch(
    body: KillSwitchRequest,
    key: object = Depends(require_permission("budget:write")),
) -> dict:
    """Set the kill-switch mode (admin). Audited + policy version bump."""
    if body.kill_switch_mode not in KILL_SWITCH_MODES:
        raise PrometheusError(
            f"Invalid kill_switch_mode: {body.kill_switch_mode}",
            code="invalid_kill_switch_mode",
            status_code=422,
        )
    actor = getattr(key, "name", "admin") or "admin"
    return set_mode(body.kill_switch_mode, actor=actor, reason=body.reason or "manual")
