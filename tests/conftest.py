"""Pytest fixtures: temp SQLite, TestClient, seeded keys, per-test cleanup.

Env vars are set at import time BEFORE any app import (settings is a singleton).
The per-process temp DB file is intentionally left in %TEMP% (no destructive
cleanup calls in test code; pytest tmp artifacts accumulate there anyway).
"""
from __future__ import annotations

import os
import tempfile

_DB_PATH = os.path.join(tempfile.gettempdir(), f"prometheus_test_{os.getpid()}.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("EMBEDDING_PROVIDER", "mock")
os.environ.setdefault("VECTOR_STORE_PROVIDER", "local")
os.environ.setdefault("CACHE_PROVIDER", "local")
os.environ.setdefault("CACHE_SIMILARITY_THRESHOLD", "0.82")
os.environ.setdefault("CACHE_TTL_SECONDS", "3600")
os.environ.setdefault("MOCK_LATENCY_CHEAP_MS", "1")
os.environ.setdefault("MOCK_LATENCY_STRONG_MS", "2")
os.environ.setdefault("DAILY_BUDGET_USD", "2.0")
os.environ.setdefault("REQUEST_BUDGET_USD", "0.05")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("APP_ENV", "test")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.security import hash_api_key  # noqa: E402
from app.db.models import ApiKey  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

ADMIN_HEADERS = {"X-API-Key": "test-admin-key"}
VIEWER_HEADERS = {"X-API-Key": "test-viewer-key"}

MUTABLE_TABLES = (
    "trace_events",
    "usage_records",
    "requests",
    "failed_requests",
    "sse_events",
    "cache_entries",
    "agent_tool_calls",
    "agent_steps",
    "agent_actions",
    "agent_runs",
    "budget_alerts",
    "audit_events",
    "eval_results",
    "eval_runs",
    "policy_changes",
)


@pytest.fixture(scope="session", autouse=True)
def _bootstrap():
    from app.db.init_db import init_db

    init_db()
    # Ingest the five seed documents so RAG grounding is available in every test
    # (mirrors scripts/seed_demo.py; the knowledge base is shared reference data).
    from app.rag.retriever import Retriever
    from app.rag.seed_content import ingest_seed_documents
    from app.providers.embeddings.base import get_embedder
    from app.vector.base import get_vector_store

    retriever = Retriever(SessionLocal, get_embedder(), get_vector_store())
    ingest_seed_documents(retriever)
    admin_hash = hash_api_key("test-admin-key")
    viewer_hash = hash_api_key("test-viewer-key")
    with SessionLocal() as s:
        if not s.query(ApiKey).filter_by(key_hash=admin_hash).first():
            s.add(ApiKey(name="test-admin", key_hash=admin_hash, role="admin"))
        if not s.query(ApiKey).filter_by(key_hash=viewer_hash).first():
            s.add(ApiKey(name="test-viewer", key_hash=viewer_hash, role="viewer"))
        s.commit()
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _cleanup():
    """Reset all mutable state + policy/kill-switch after every test."""
    yield
    with engine.begin() as conn:
        for table in MUTABLE_TABLES:
            conn.execute(text(f"DELETE FROM {table}"))
    from app.governance.policy_engine import DEFAULT_POLICY, update_policy

    update_policy(dict(DEFAULT_POLICY), actor="test", reason="cleanup")


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def admin_headers() -> dict:
    return dict(ADMIN_HEADERS)


@pytest.fixture()
def viewer_headers() -> dict:
    return dict(VIEWER_HEADERS)


@pytest.fixture()
def run_chat(client):
    """POST /api/v1/chat helper (admin by default)."""

    def _run(query: str, headers: dict | None = None, **kw):
        body = {"query": query, **kw}
        return client.post("/api/v1/chat", json=body, headers=headers or ADMIN_HEADERS)

    return _run
