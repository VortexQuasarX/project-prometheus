"""POST /api/v1/agents/run + GET /api/v1/agents/runs[/{run_id}] — agent runtime."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.agents.orchestrator import create_run, get_run, list_runs
from app.agents.schemas import AgentRunCreate
from app.core.errors import PrometheusError
from app.core.rbac import require_permission

router = APIRouter()


@router.post("/agents/run")
def run_agent(body: AgentRunCreate, key: object = Depends(require_permission("agents:run"))) -> dict:
    """Create + synchronously execute an agent run (finops / reliability / ...)."""
    try:
        return create_run(
            body.agent_type,
            body.trigger,
            params=body.params,
            organization_id=getattr(key, "organization_id", None),
        )
    except ValueError as exc:
        raise PrometheusError(str(exc), code="invalid_agent_request", status_code=422) from exc


@router.get("/agents/runs")
def runs(
    status: str | None = None,
    agent_type: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    key: object = Depends(require_permission("agents:read")),
) -> dict:
    """List agent runs (summaries, org-scoped)."""
    return list_runs(status=status, agent_type=agent_type, limit=limit, offset=offset, organization_id=getattr(key, "organization_id", None))


@router.get("/agents/runs/{run_id}")
def run_detail(run_id: str, key: object = Depends(require_permission("agents:read"))) -> dict:
    """Full agent run detail: plan, steps, tool calls, observations, outcome."""
    try:
        return get_run(run_id)
    except KeyError as exc:
        raise PrometheusError(
            f"Unknown run_id: {run_id}", code="not_found", status_code=404
        ) from exc
