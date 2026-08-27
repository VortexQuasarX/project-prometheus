"""GET /api/v1/budget + POST /api/v1/budget/kill-switch — FinOps control."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.errors import PrometheusError
from app.core.security import require_admin, require_api_key
from app.governance.budget import get_budget_status
from app.governance.kill_switch import KILL_SWITCH_MODES, set_mode

router = APIRouter()


class KillSwitchRequest(BaseModel):
    kill_switch_mode: str = Field(..., pattern="^(off|cache_only|cheap_only|block_all)$")
    reason: str | None = Field(default=None, max_length=500)


@router.get("/budget")
def budget(_: object = Depends(require_api_key)) -> dict:
    """Daily/monthly spend, budget state, kill-switch mode, recommendations."""
    return get_budget_status()


@router.post("/budget/kill-switch")
def kill_switch(
    body: KillSwitchRequest,
    key: object = Depends(require_admin),
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
