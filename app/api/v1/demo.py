"""POST /api/v1/demo/reset — restore the recruiter-demo state (admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import require_admin

router = APIRouter()


@router.post("/demo/reset")
def demo_reset(_: object = Depends(require_admin)) -> dict:
    """Wipe and reseed the demo database (idempotent; audited by the reset itself)."""
    from scripts.reset_demo import reset  # lazy: script module

    return reset()
