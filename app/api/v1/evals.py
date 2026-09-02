"""Evaluation harness endpoints: POST /evals/run, GET /evals/runs[/{run_id}].

The runner lives in ``app.eval.runner`` (lazy-imported) so this router is
independent of the harness implementation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.errors import PrometheusError
from app.core.rbac import require_permission

router = APIRouter()


class EvalRunRequest(BaseModel):
    limit: int | None = Field(default=None, ge=1, le=100)
    golden_set: str | None = Field(default=None, max_length=64)


@router.post("/evals/run")
def run_evals_endpoint(
    body: EvalRunRequest | None = None,
    key: object = Depends(require_permission("evals:run")),
) -> dict:
    """Run the golden-set evaluation harness through the in-process chat pipeline."""
    from app.eval.runner import run_evals  # lazy: harness slice

    return run_evals(
        limit=body.limit if body else None,
        golden_set=body.golden_set if body else None,
        organization_id=getattr(key, "organization_id", None),
    )


@router.get("/evals/runs")
def eval_runs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    key: object = Depends(require_permission("evals:read")),
) -> dict:
    from app.eval.runner import list_eval_runs  # lazy

    return list_eval_runs(limit=limit, offset=offset, organization_id=getattr(key, "organization_id", None))


@router.get("/evals/runs/{run_id}")
def eval_run_detail(run_id: str, _: object = Depends(require_permission("evals:read"))) -> dict:
    from app.eval.runner import get_eval_run  # lazy

    try:
        return get_eval_run(run_id)
    except KeyError as exc:
        raise PrometheusError(
            f"Unknown eval run: {run_id}", code="not_found", status_code=404
        ) from exc
