"""POST /api/v1/agents/run + GET /api/v1/agents/runs[/{run_id}] — agent runtime."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.agents.orchestrator import create_run, get_run, list_runs
from app.agents.schemas import AgentRunCreate
from app.core.errors import PrometheusError
from app.core.security import require_admin, require_api_key

router = APIRouter()


@router.post("/agents/run")
def run_agent(body: AgentRunCreate, _: object = Depends(require_admin)) -> dict:
    """Create + synchronously execute an agent run (finops / reliability / ...)."""
    try:
        return create_run(body.agent_type, body.trigger, params=body.params)
    except ValueError as exc:
        raise PrometheusError(str(exc), code="invalid_agent_request", status_code=422) from exc


@router.get("/agents/runs")
def runs(
    status: str | None = None,
    agent_type: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: object = Depends(require_api_key),
) -> dict:
    """List agent runs (summaries)."""
    return list_runs(status=status, agent_type=agent_type, limit=limit, offset=offset)


@router.get("/agents/runs/{run_id}")
def run_detail(run_id: str, _: object = Depends(require_api_key)) -> dict:
    """Full agent run detail: plan, steps, tool calls, observations, outcome."""
    try:
        return get_run(run_id)
    except KeyError as exc:
        raise PrometheusError(
            f"Unknown run_id: {run_id}", code="not_found", status_code=404
        ) from exc
