"""GET/PUT /api/v1/policies — policy engine surface (admin edit, audited)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.errors import PrometheusError
from app.core.security import require_admin
from app.governance.policy_engine import get_policy, update_policy

router = APIRouter()


class PolicyUpdate(BaseModel):
    """Full policy body replacement (validated against PolicySchema)."""

    policy: dict
    reason: str = Field(min_length=1, max_length=500)


@router.get("/policies")
def policies(_: object = Depends(require_admin)) -> dict:
    """Return the active policy, its version and last update time."""
    policy, version = get_policy()
    return {"policy": policy, "policy_version": version}


@router.put("/policies")
def update_policies(body: PolicyUpdate, key: object = Depends(require_admin)) -> dict:
    """Replace the active policy. Audited + version-bumped (cache invalidation)."""
    actor = getattr(key, "name", "admin") or "admin"
    try:
        new_body, version = update_policy(body.policy, actor=actor, reason=body.reason)
    except Exception as exc:
        raise PrometheusError(
            f"Invalid policy: {exc}",
            code="invalid_policy",
            status_code=422,
        ) from exc
    return {"policy": new_body, "policy_version": version}
