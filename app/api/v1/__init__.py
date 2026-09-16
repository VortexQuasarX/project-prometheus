"""API v1 router aggregation.

Every endpoint lives under ``/api/v1`` (registered in ``app.main``).
Auth matrix (see docs/GOVERNANCE.md): health public, GETs viewer+,
mutating endpoints admin, chat viewer+.
"""

from fastapi import APIRouter

from app.api.v1 import (
    agents,
    approvals,
    audit,
    budget,
    cache,
    chat,
    cost,
    demo,
    evals,
    events,
    health,
    ingest,
    metrics,
    policies,
    traces,
    redteam,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(ingest.router, tags=["ingest"])
api_router.include_router(metrics.router, tags=["metrics"])
api_router.include_router(cost.router, tags=["cost"])
api_router.include_router(cache.router, tags=["cache"])
api_router.include_router(traces.router, tags=["traces"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(policies.router, tags=["policies"])
api_router.include_router(budget.router, tags=["budget"])
api_router.include_router(agents.router, tags=["agents"])
api_router.include_router(approvals.router, tags=["approvals"])
api_router.include_router(evals.router, tags=["evals"])
api_router.include_router(audit.router, tags=["audit"])
api_router.include_router(demo.router, tags=["demo"])
api_router.include_router(redteam.router, tags=["redteam"])

__all__ = ["api_router"]
