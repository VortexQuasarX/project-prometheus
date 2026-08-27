"""GET /api/v1/audit — immutable audit trail (admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.security import require_admin
from app.governance.audit import query as audit_query

router = APIRouter()


@router.get("/audit")
def audit_list(
    actor: str | None = None,
    action: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: object = Depends(require_admin),
) -> dict:
    """Query audit events (newest first), optionally filtered by actor/action."""
    events = audit_query(actor=actor, action=action, limit=limit, offset=offset)
    items = [e.to_dict() for e in events]
    return {"items": items, "total": len(items)}
