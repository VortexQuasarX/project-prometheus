"""RBAC permission matrix + multi-tenant isolation tests.

Role fixtures are created per-organization; every protected operation is
asserted against the server-side permission matrix, and cross-tenant
visibility is asserted to be empty.
"""
from __future__ import annotations

import pytest

from app.core.rbac import normalize_role, role_has
from app.core.security import hash_api_key
from app.db.models import ApiKey, Organization
from app.db.session import SessionLocal

ROLES = ["super_admin", "org_admin", "developer", "analyst", "auditor", "viewer"]

PERMISSION_MATRIX = {
    # permission -> (method, path, body or None)
    "agents:run": ("POST", "/api/v1/agents/run", {"agent_type": "finops", "trigger": "manual"}),
    "approvals:decide": ("POST", "/api/v1/agents/actions/does-not-exist/approve", {"note": "x"}),
    "policies:write": ("PUT", "/api/v1/policies", {"policy": None, "reason": "t"}),
    "budget:write": ("POST", "/api/v1/budget/kill-switch", {"kill_switch_mode": "off", "reason": "t"}),
    "evals:run": ("POST", "/api/v1/evals/run", {}),
    "demo:reset": ("POST", "/api/v1/demo/reset", {}),
    "documents:write": ("POST", "/api/v1/ingest", {"title": "t", "content": "c"}),
    "audit:read": ("GET", "/api/v1/audit", None),
}

# which roles hold each permission (mirror of app/core/rbac.py)
HOLDERS = {
    "agents:run": {"super_admin", "org_admin"},
    "approvals:decide": {"super_admin", "org_admin"},
    "policies:write": {"super_admin", "org_admin"},
    "budget:write": {"super_admin", "org_admin"},
    "evals:run": {"super_admin", "org_admin", "developer"},
    "demo:reset": {"super_admin", "org_admin"},
    "documents:write": {"super_admin", "org_admin", "developer"},
    "audit:read": {"super_admin", "org_admin", "auditor"},
}


@pytest.fixture(scope="module")
def role_keys():
    """One API key per role, all in org_role_test."""
    from sqlalchemy import select

    with SessionLocal() as s:
        if s.scalar(select(Organization).where(Organization.id == "org_role_test")) is None:
            s.add(Organization(id="org_role_test", name="RBAC Test Org", slug="rbac-test"))
        for role in ROLES:
            kh = hash_api_key(f"rbac-{role}-key")
            if s.scalar(select(ApiKey).where(ApiKey.key_hash == kh)) is None:
                s.add(
                    ApiKey(
                        name=f"rbac-{role}",
                        key_hash=kh,
                        role=role,
                        organization_id="org_role_test",
                    )
                )
        s.commit()
    return {role: {"X-API-Key": f"rbac-{role}-key"} for role in ROLES}


@pytest.mark.parametrize("role", ROLES)
def test_role_permission_matrix(client, role_keys, role):
    """Every protected endpoint returns non-403 only for roles holding the permission."""
    headers = role_keys[role]
    for permission, (method, path, body) in PERMISSION_MATRIX.items():
        if permission == "demo:reset" and role_has(role, permission):
            # demo:reset wipes the database — holders are covered by the
            # permission dependency; executing it here would destroy the
            # fixture state for every later assertion.
            continue
        kwargs = {"headers": headers}
        if body is not None:
            payload = dict(body)
            if path.endswith("/policies"):
                from app.governance.policy_engine import DEFAULT_POLICY

                payload["policy"] = dict(DEFAULT_POLICY)
            kwargs["json"] = payload
        response = getattr(client, method.lower())(path, **kwargs)
        holds = role_has(role, permission)
        if holds:
            assert response.status_code != 403, (
                f"{role} should hold {permission}: got {response.status_code} on {path}"
            )
        else:
            assert response.status_code == 403, (
                f"{role} should NOT hold {permission}: got {response.status_code} on {path}"
            )


def test_legacy_admin_role_maps_to_super_admin():
    assert normalize_role("admin") == "super_admin"
    assert role_has("admin", "keys:manage")


def test_unknown_role_falls_back_to_viewer():
    assert normalize_role("mystery") == "viewer"
    assert not role_has("mystery", "policies:write")


def test_cross_tenant_isolation(client, role_keys):
    """Org A's chat trace must be invisible to org B's keys."""
    from sqlalchemy import select

    with SessionLocal() as s:
        if s.scalar(select(Organization).where(Organization.id == "org_a")) is None:
            s.add(Organization(id="org_a", name="Org A", slug="org-a"))
        if s.scalar(select(Organization).where(Organization.id == "org_b")) is None:
            s.add(Organization(id="org_b", name="Org B", slug="org-b"))
        for org, key in (("org_a", "iso-a-key"), ("org_b", "iso-b-key")):
            kh = hash_api_key(key)
            if s.scalar(select(ApiKey).where(ApiKey.key_hash == kh)) is None:
                s.add(ApiKey(name=org, key_hash=kh, role="org_admin", organization_id=org))
        s.commit()

    headers_a = {"X-API-Key": "iso-a-key"}
    headers_b = {"X-API-Key": "iso-b-key"}
    r = client.post(
        "/api/v1/chat",
        json={"query": "Cross tenant isolation probe unique string"},
        headers=headers_a,
    )
    assert r.status_code == 200, r.text
    request_id = r.json()["request_id"]

    # org A sees it
    traces_a = client.get("/api/v1/traces?limit=200", headers=headers_a).json()
    assert any(t["request_id"] == request_id for t in traces_a["items"])

    # org B does NOT see it
    traces_b = client.get("/api/v1/traces?limit=200", headers=headers_b).json()
    assert not any(t["request_id"] == request_id for t in traces_b["items"])

    # direct trace fetch from org B -> 404 (invisible)
    detail_b = client.get(f"/api/v1/traces/{request_id}", headers=headers_b)
    assert detail_b.status_code == 404
