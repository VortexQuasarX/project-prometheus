"""Role-based access control (enterprise RBAC).

Roles: super_admin | org_admin | developer | analyst | auditor | viewer
(legacy ``admin`` is accepted everywhere as ``super_admin``).

Permissions are enforced server-side via ``require_permission(...)`` FastAPI
dependencies. Tenant isolation: API keys belong to an Organization; list/read
endpoints scope queries to the caller's organization via ``tenant_scope``.
"""
from __future__ import annotations

from fastapi import Depends

from app.core.errors import PrometheusError
from app.core.security import get_api_key
from app.db.models import ApiKey

__all__ = [
    "ROLES",
    "ROLE_PERMISSIONS",
    "normalize_role",
    "role_has",
    "require_permission",
    "require_super_admin",
    "tenant_scope",
]

ROLES = ("super_admin", "org_admin", "developer", "analyst", "auditor", "viewer", "admin")

_READ_BASE = frozenset({"metrics:read", "cost:read", "cache:read", "traces:read", "agents:read"})

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "super_admin": frozenset(
        {
            "chat:run", "documents:write", "metrics:read", "cost:read", "cache:read",
            "traces:read", "policies:read", "policies:write", "budget:read",
            "budget:write", "agents:read", "agents:run", "approvals:decide",
            "evals:read", "evals:run", "audit:read", "demo:reset", "keys:manage",
            "org:manage",
        }
    ),
    "org_admin": frozenset(
        {
            "chat:run", "documents:write", "metrics:read", "cost:read", "cache:read",
            "traces:read", "policies:read", "policies:write", "budget:read",
            "budget:write", "agents:read", "agents:run", "approvals:decide",
            "evals:read", "evals:run", "audit:read", "demo:reset",
        }
    ),
    "developer": frozenset(
        {
            "chat:run", "documents:write", "metrics:read", "cost:read", "cache:read",
            "traces:read", "policies:read", "budget:read", "agents:read",
            "evals:read", "evals:run",
        }
    ),
    "analyst": frozenset(
        {
            "chat:run", "metrics:read", "cost:read", "cache:read", "traces:read",
            "policies:read", "budget:read", "agents:read", "evals:read",
        }
    ),
    "auditor": frozenset(
        {
            "metrics:read", "cost:read", "cache:read", "traces:read",
            "policies:read", "budget:read", "agents:read", "evals:read",
            "audit:read",
        }
    ),
    "viewer": frozenset({"chat:run", "metrics:read", "cache:read", "traces:read", "agents:read"}),
}


# legacy alias: the original MVP "admin" role keeps full super-admin powers.
ROLE_PERMISSIONS["admin"] = ROLE_PERMISSIONS["super_admin"]


def normalize_role(role: str | None) -> str:
    """Map legacy/unknown roles onto the canonical vocabulary."""
    role = (role or "viewer").strip().lower()
    if role == "admin":
        return "super_admin"
    return role if role in ROLE_PERMISSIONS else "viewer"


def role_has(role: str | None, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(normalize_role(role), frozenset())


def require_permission(permission: str):
    """FastAPI dependency factory: enforce a server-side permission."""

    def dependency(key: ApiKey = Depends(get_api_key)) -> ApiKey:
        if not role_has(key.role, permission):
            raise PrometheusError(
                f"Missing required permission: {permission}",
                code="forbidden",
                status_code=403,
            )
        return key

    return dependency


def require_super_admin(key: ApiKey = Depends(get_api_key)) -> ApiKey:
    if normalize_role(key.role) != "super_admin":
        raise PrometheusError("Super admin privileges required", code="forbidden", status_code=403)
    return key


def tenant_scope(query, model, key: ApiKey):
    """Scope ``query`` on ``model`` to the caller's organization.

    Super admins (organization_id IS NULL on their key) see everything;
    organization-scoped keys see their org's rows plus global rows (NULL org).
    """
    org_id = getattr(key, "organization_id", None)
    if not org_id or not hasattr(model, "organization_id"):
        return query
    from sqlalchemy import or_

    return query.filter(
        or_(model.organization_id == org_id, model.organization_id.is_(None))
    )
