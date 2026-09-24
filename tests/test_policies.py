"""Policy engine: defaults, audited updates, validation, kill-switch enforcement."""

from app.governance.policy_engine import DEFAULT_POLICY

SPEC_FIELDS = (
    "daily_budget_usd",
    "request_budget_usd",
    "max_input_tokens",
    "max_output_tokens",
    "allowed_models",
    "expensive_model_limit_per_day",
    "require_cache_check",
    "require_rag",
    "require_evaluation",
    "require_human_approval",
    "pii_masking_enabled",
    "prompt_injection_detection_enabled",
    "rate_limit_per_minute",
    "kill_switch_mode",
)


def test_get_default_policy(client, admin_headers):
    body = client.get("/api/v1/policies", headers=admin_headers).json()
    policy = body["policy"]
    for field in SPEC_FIELDS:
        assert field in policy, f"missing {field}"
    assert policy["daily_budget_usd"] == 2.0
    assert policy["request_budget_usd"] == 0.05
    assert policy["allowed_models"] == DEFAULT_POLICY["allowed_models"]
    assert policy["kill_switch_mode"] == "off"
    assert body["policy_version"] >= 1


def test_put_policy_is_audited(client, admin_headers):
    before = client.get("/api/v1/policies", headers=admin_headers).json()
    new_policy = dict(before["policy"])
    new_policy["daily_budget_usd"] = 1.5
    put = client.put(
        "/api/v1/policies",
        json={"policy": new_policy, "reason": "unit test update"},
        headers=admin_headers,
    )
    assert put.status_code == 200, put.text
    assert put.json()["policy_version"] == before["policy_version"] + 1
    assert put.json()["policy"]["daily_budget_usd"] == 1.5

    audit = client.get("/api/v1/audit", headers=admin_headers).json()
    actions = [e["action"] for e in audit["items"]]
    assert "policy.updated" in actions


def test_put_policy_invalid_returns_422(client, admin_headers):
    bad = dict(DEFAULT_POLICY)
    bad["daily_budget_usd"] = -5
    r = client.put(
        "/api/v1/policies",
        json={"policy": bad, "reason": "bad input"},
        headers=admin_headers,
    )
    assert r.status_code == 422


def test_kill_switch_cheap_only_blocks_strong_model(client, admin_headers):
    client.post(
        "/api/v1/budget/kill-switch",
        json={"kill_switch_mode": "cheap_only", "reason": "test"},
        headers=admin_headers,
    )
    r = client.post(
        "/api/v1/chat",
        json={"query": "cheap_only strong model probe unique omega", "model": "mock-large"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["estimated_cost_usd"] == 0.0
    assert body["guardrail_status"] == "blocked_kill_switch"


def test_kill_switch_block_all_403(client, admin_headers):
    client.post(
        "/api/v1/budget/kill-switch",
        json={"kill_switch_mode": "block_all", "reason": "test"},
        headers=admin_headers,
    )
    r = client.post("/api/v1/chat", json={"query": "block all probe"}, headers=admin_headers)
    assert r.status_code == 403
