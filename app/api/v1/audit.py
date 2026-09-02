"""GET /api/v1/audit — immutable audit trail (admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.rbac import require_permission
from app.governance.audit import query as audit_query

router = APIRouter()


@router.get("/audit")
def audit_list(
    actor: str | None = None,
    action: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    key: object = Depends(require_permission("audit:read")),
) -> dict:
    """Query audit events (newest first, org-scoped), optionally filtered by actor/action."""
    events = audit_query(actor=actor, action=action, limit=limit, offset=offset, organization_id=getattr(key, "organization_id", None))
    items = [e.to_dict() for e in events]
    return {"items": items, "total": len(items)}
