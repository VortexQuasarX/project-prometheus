"""Agent approvals: GET /agents/actions + POST approve/reject.

The spec defines approve/reject only; ``GET /agents/actions`` is a documented
spec-gap fix so the Approvals page has a list source (see docs/ARCHITECTURE.md).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.agents.schemas import DecisionRequest
from app.core.errors import PrometheusError
from app.core.security import require_admin, require_api_key
from app.governance.approvals import decide_action, list_pending_actions

router = APIRouter()


class _ActionEnvelope(BaseModel):
    items: list[dict]


@router.get("/agents/actions")
def pending_actions(
    status: str = Query("pending"),
    _: object = Depends(require_api_key),
) -> _ActionEnvelope:
    """List agent actions, defaulting to pending (Approvals page source)."""
    if status != "pending":
        # MVP only exposes pending actions; other statuses are visible via run detail.
        return _ActionEnvelope(items=[])
    actions = list_pending_actions()
    return _ActionEnvelope(items=[_action_to_dict(a) for a in actions])


def _action_to_dict(action: object) -> dict:
    d = {
        "action_id": getattr(action, "action_id", ""),
        "title": getattr(action, "title", ""),
        "expected_monthly_saving_usd": float(
            getattr(action, "expected_monthly_saving_usd", 0.0) or 0.0
        ),
        "risk_level": getattr(action, "risk_level", "low"),
        "latency_impact": getattr(action, "latency_impact", "minimal"),
        "approval_required": bool(getattr(action, "approval_required", True)),
        "status": getattr(action, "status", "pending"),
    }
    run_id = getattr(action, "run_id", None)
    if run_id:
        d["run_id"] = run_id
    return d


@router.post("/agents/actions/{action_id}/approve")
def approve_action(
    action_id: str,
    body: DecisionRequest | None = None,
    key: object = Depends(require_admin),
) -> dict:
    """Approve a pending FinOps action -> applies the policy delta (audited)."""
    actor = getattr(key, "name", "admin") or "admin"
    note = body.note if body else None
    try:
        return decide_action(action_id, "approve", actor=actor, note=note)
    except KeyError as exc:
        raise PrometheusError(
            f"Unknown action_id: {action_id}", code="not_found", status_code=404
        ) from exc
    except ValueError as exc:
        raise PrometheusError(str(exc), code="invalid_action_state", status_code=409) from exc


@router.post("/agents/actions/{action_id}/reject")
def reject_action(
    action_id: str,
    body: DecisionRequest | None = None,
    key: object = Depends(require_admin),
) -> dict:
    """Reject a pending FinOps action (audited)."""
    actor = getattr(key, "name", "admin") or "admin"
    note = body.note if body else None
    try:
        return decide_action(action_id, "reject", actor=actor, note=note)
    except KeyError as exc:
        raise PrometheusError(
            f"Unknown action_id: {action_id}", code="not_found", status_code=404
        ) from exc
    except ValueError as exc:
        raise PrometheusError(str(exc), code="invalid_action_state", status_code=409) from exc
