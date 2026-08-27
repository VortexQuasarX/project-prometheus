"""Semantic cache: miss->hit, near-duplicate, TTL, stats, policy invalidation."""

from datetime import UTC, datetime


def test_cache_miss_then_hit(run_chat):
    q = "What is semantic caching in LLM gateways?"
    r1 = run_chat(q)
    assert r1.status_code == 200
    assert r1.json()["cache_hit"] is False
    r2 = run_chat(q)
    assert r2.json()["cache_hit"] is True
    assert r2.json()["cost_saved_usd"] > 0


def test_cache_near_duplicate_hits(run_chat):
    run_chat("How does semantic caching reduce LLM costs for teams?")
    r2 = run_chat("How does semantic caching reduce LLM cost for teams?")
    assert r2.json()["cache_hit"] is True


def test_cache_ttl_expiry(run_chat):
    q = "Unique TTL expiry probe epsilon"
    run_chat(q)

    from app.db.models import CacheEntry
    from app.db.session import SessionLocal

    with SessionLocal() as s:
        for row in s.query(CacheEntry).all():
            row.expires_at = datetime(2020, 1, 1, tzinfo=UTC)
        s.commit()
    r2 = run_chat(q)
    assert r2.json()["cache_hit"] is False


def test_cache_stats_shape(client, admin_headers, run_chat):
    run_chat("Cache stats shape probe zeta")
    stats = client.get("/api/v1/cache-stats", headers=admin_headers).json()
    for key in (
        "hit_count",
        "miss_count",
        "hit_rate",
        "entry_count",
        "total_cost_saved_usd",
        "threshold",
        "ttl_seconds",
        "policy_version",
        "kb_version",
        "cache_version",
    ):
        assert key in stats, f"missing {key}"
    assert stats["threshold"] == 0.82
    assert stats["ttl_seconds"] == 3600


def test_policy_update_invalidates_cache(client, admin_headers, run_chat):
    q = "Policy version invalidation probe eta"
    run_chat(q)
    assert run_chat(q).json()["cache_hit"] is True

    current = client.get("/api/v1/policies", headers=admin_headers).json()["policy"]
    put = client.put(
        "/api/v1/policies",
        json={"policy": current, "reason": "cache invalidation test"},
        headers=admin_headers,
    )
    assert put.status_code == 200, put.text

    r3 = run_chat(q)
    assert r3.json()["cache_hit"] is False
