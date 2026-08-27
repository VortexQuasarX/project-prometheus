"""Database bootstrap: create tables and seed if empty.

Seeding is idempotent: default policy (spec JSON + ``expensive_models``),
5 seed documents (lazy-imported from ``app.rag.seed_content`` so this module
compiles before that slice exists), and admin/viewer API keys.
"""

from __future__ import annotations

import logging
import secrets
from typing import Any

from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import hash_api_key
from app.db.base import Base
from app.db.models import ApiKey, Document, Policy
from app.db.session import SessionLocal, engine

logger = logging.getLogger("prometheus.init_db")

DEFAULT_POLICY: dict[str, Any] = {
    "daily_budget_usd": 2.0,
    "request_budget_usd": 0.05,
    "max_input_tokens": 1000,
    "max_output_tokens": 500,
    "allowed_models": ["mock-small", "mock-large"],
    "expensive_models": ["mock-large", "bedrock-strong"],
    "expensive_model_limit_per_day": 20,
    "require_cache_check": True,
    "require_rag": True,
    "require_evaluation": True,
    "require_human_approval": True,
    "pii_masking_enabled": True,
    "prompt_injection_detection_enabled": True,
    "rate_limit_per_minute": 30,
    "kill_switch_mode": "off",
}

_FALLBACK_SEED_DOCUMENTS: list[dict[str, str]] = [
    {
        "document_id": "doc_01",
        "title": "AI Cost Governance",
        "content": (
            "AI cost governance is the discipline of monitoring, budgeting, and optimizing "
            "spend on AI services. Prometheus tracks daily and monthly spend, enforces "
            "request-level budgets, and activates kill switches when budgets are exceeded. "
            "Caching, model routing, and FinOps actions reduce waste."
        ),
        "source": "seed",
    },
    {
        "document_id": "doc_02",
        "title": "LLM Cache Optimization",
        "content": (
            "Semantic caching stores embeddings of queries and answers. A new query is "
            "compared by cosine similarity against cached entries; matches above the "
            "similarity threshold reuse the stored answer. TTL, policy version, and "
            "knowledge base version gate cache validity."
        ),
        "source": "seed",
    },
    {
        "document_id": "doc_03",
        "title": "AWS Bedrock Cost Controls",
        "content": (
            "Amazon Bedrock bills per token by model. Prometheus maps Bedrock models to "
            "explicit price tables, prefers cheaper models for simple queries, blocks "
            "expensive models after a daily limit, and can force cache-only or cheap-only "
            "modes via the kill switch."
        ),
        "source": "seed",
    },
    {
        "document_id": "doc_04",
        "title": "AI Guardrails Overview",
        "content": (
            "Guardrails protect users and systems: PII detection and masking, unsafe-content "
            "blocking, prompt-injection heuristics, restricted-topic filters, and budget "
            "checks. Blocked requests return a safe refusal, log an audit event, and never "
            "call the LLM."
        ),
        "source": "seed",
    },
    {
        "document_id": "doc_05",
        "title": "FinOps for AI",
        "content": (
            "FinOps for AI applies financial governance to model usage: detect inefficiency "
            "(expensive-model overuse, low cache hit rate, rising latency), estimate savings, "
            "request human approval, apply policy changes, and verify the outcome."
        ),
        "source": "seed",
    },
]


def _load_default_policy() -> dict[str, Any]:
    """Prefer the policy-engine slice's canonical default; fall back to local copy."""
    try:
        from app.governance.policy_engine import DEFAULT_POLICY as canonical_policy

        if isinstance(canonical_policy, dict) and canonical_policy:
            return dict(canonical_policy)
    except Exception:  # pragma: no cover — slice not built yet
        pass
    return dict(DEFAULT_POLICY)


def _load_seed_documents() -> list[dict[str, Any]]:
    """Lazy-import seed content from the RAG slice; fall back to local copies."""
    try:
        from app.rag.seed_content import SEED_DOCUMENTS

        if isinstance(SEED_DOCUMENTS, list) and SEED_DOCUMENTS:
            return [dict(doc) for doc in SEED_DOCUMENTS]
    except Exception:  # pragma: no cover — slice not built yet
        logger.info("app.rag.seed_content not available; using built-in seed documents")
    return [dict(doc) for doc in _FALLBACK_SEED_DOCUMENTS]


def _resolve_admin_key() -> str:
    """Use the env admin key when set (and not the ``***`` placeholder)."""
    candidate = settings.admin_api_key.strip() if settings.admin_api_key else ""
    if candidate and candidate != "***":
        return candidate
    generated = f"prometheus-demo-admin-{secrets.token_hex(8)}"
    logger.info("Generated demo admin API key (not from env): %s", generated)
    return generated


def _create_api_keys(session: Any) -> tuple[str, str]:
    admin_raw = _resolve_admin_key()
    session.add(
        ApiKey(key_hash=hash_api_key(admin_raw), name="admin", role="admin", is_active=True)
    )
    viewer_raw = f"prometheus-demo-viewer-{secrets.token_hex(8)}"
    session.add(
        ApiKey(key_hash=hash_api_key(viewer_raw), name="viewer", role="viewer", is_active=True)
    )
    return admin_raw, viewer_raw


def seed_if_empty() -> dict[str, Any]:
    """Seed default policy, seed documents, and demo API keys when tables are empty."""
    seeded: dict[str, Any] = {
        "policies": 0,
        "documents": 0,
        "api_keys": 0,
        "admin_api_key": None,
        "viewer_api_key": None,
    }
    with SessionLocal() as session:
        if session.scalar(select(func.count(ApiKey.id))) == 0:
            admin_raw, viewer_raw = _create_api_keys(session)
            seeded["api_keys"] = 2
            seeded["admin_api_key"] = admin_raw
            seeded["viewer_api_key"] = viewer_raw
        elif settings.admin_api_key and settings.admin_api_key != "***":
            seeded["admin_api_key"] = settings.admin_api_key

        if session.scalar(select(func.count(Policy.id))) == 0:
            session.add(Policy(policy_version=1, body=_load_default_policy(), is_active=True))
            seeded["policies"] = 1

        if session.scalar(select(func.count(Document.id))) == 0:
            for doc in _load_seed_documents():
                doc_index = seeded["documents"] + 1
                document_id = str(doc.get("document_id") or "").strip() or f"doc_{doc_index:02d}"
                session.add(
                    Document(
                        document_id=document_id,
                        title=str(doc.get("title") or "Untitled"),
                        source=str(doc.get("source") or "seed"),
                        details=doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {},
                        kb_version=1,
                    )
                )
                seeded["documents"] += 1

        session.commit()
    logger.info("seed_if_empty complete: %s", seeded)
    return seeded


def init_db() -> dict[str, Any]:
    """Create all tables, then seed-if-empty. Returns seeded counts + demo keys."""
    Base.metadata.create_all(bind=engine)
    return seed_if_empty()
