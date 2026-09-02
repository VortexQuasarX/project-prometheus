"""POST /api/v1/chat: schema, auth, validation, audit, idempotency, kill switch."""

REQUIRED_FIELDS = (
    "request_id",
    "answer",
    "provider",
    "model",
    "router_decision",
    "cache_hit",
    "estimated_cost_usd",
    "cost_saved_usd",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "guardrail_status",
    "evaluation_score",
    "citations",
    "trace_url",
)

ROUTER_DECISIONS = {
    "CACHE_ONLY",
    "CHEAP_MODEL",
    "STRONG_MODEL",
    "GUARDRAIL_REVIEW",
    "REJECT",
    "CLARIFY",
}


def test_chat_200_full_schema(run_chat, admin_headers):
    r = run_chat("Explain how AI cost governance works for platform teams")
    assert r.status_code == 200, r.text
    body = r.json()
    for field in REQUIRED_FIELDS:
        assert field in body, f"missing field {field}"
    assert body["router_decision"] in ROUTER_DECISIONS
    assert isinstance(body["cache_hit"], bool)
    assert isinstance(body["estimated_cost_usd"], (int, float))
    assert body["trace_url"].startswith("/api/v1/traces/")
    assert isinstance(body["citations"], list)
    assert body["answer"]


def test_chat_requires_api_key(client):
    r = client.post("/api/v1/chat", json={"query": "hello world"})
    assert r.status_code == 401
    body = r.json()
    assert "error" in body or "detail" in body


def test_chat_rejects_bad_api_key(client):
    r = client.post("/api/v1/chat", json={"query": "hello world"}, headers={"X-API-Key": "wrong-key"})
    assert r.status_code == 401


def test_chat_422_on_empty_query(client, admin_headers):
    r = client.post("/api/v1/chat", json={"query": ""}, headers=admin_headers)
    assert r.status_code == 422


def test_chat_writes_audit_event(client, admin_headers, run_chat):
    run_chat("Audit trail probe query alpha")
    audit = client.get("/api/v1/audit", headers=admin_headers).json()
    actions = [e["action"] for e in audit.get("items", [])]
    assert "chat.request" in actions


def test_chat_idempotent_replay(client, admin_headers):
    body = {"query": "Idempotency replay probe query beta"}
    headers = {**admin_headers, "X-Idempotency-Key": "idem-test-001"}
    r1 = client.post("/api/v1/chat", json=body, headers=headers)
    assert r1.status_code == 200
    r2 = client.post("/api/v1/chat", json=body, headers=headers)
    assert r2.status_code == 200
    assert r1.json()["request_id"] == r2.json()["request_id"]


def test_chat_block_all_returns_403(client, admin_headers):
    ks = client.post(
        "/api/v1/budget/kill-switch",
        json={"kill_switch_mode": "block_all", "reason": "test"},
        headers=admin_headers,
    )
    assert ks.status_code == 200
    r = client.post("/api/v1/chat", json={"query": "blocked probe"}, headers=admin_headers)
    assert r.status_code == 403
    body = r.json()
    assert "error" in body


def test_chat_cache_only_mode_no_llm_call(client, admin_headers):
    client.post(
        "/api/v1/budget/kill-switch",
        json={"kill_switch_mode": "cache_only", "reason": "test"},
        headers=admin_headers,
    )
    r = client.post(
        "/api/v1/chat",
        json={"query": "Unique cache-only refusal probe gamma"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["cache_hit"] is False
    assert body["estimated_cost_usd"] == 0.0
    timeline = client.get(
        f"/api/v1/traces/{body['request_id']}", headers=admin_headers
    ).json()["timeline"]
    assert "llm_called" not in [e["name"] for e in timeline], (
        "cache_only mode must never call the LLM"
    )


def test_viewer_can_chat_but_not_admin(client, viewer_headers):
    r = client.post("/api/v1/chat", json={"query": "viewer role probe delta"}, headers=viewer_headers)
    assert r.status_code == 200
    forbidden = client.post(
        "/api/v1/agents/run",
        json={"agent_type": "finops", "trigger": "manual"},
        headers=viewer_headers,
    )
    assert forbidden.status_code == 403
