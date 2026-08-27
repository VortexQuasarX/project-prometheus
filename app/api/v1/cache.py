"""GET /api/v1/cache-stats — semantic cache statistics."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.cache.semantic_cache import SemanticCache
from app.core.config import settings
from app.core.security import require_api_key
from app.db.session import get_db
from app.governance.policy_engine import get_policy


def _cache() -> SemanticCache:
    """Build the shared SemanticCache wired to live policy/kb versions."""
    policy, policy_version = get_policy()

    def _kb_version() -> int:
        try:
            from app.rag.retriever import Retriever
            from app.providers.embeddings.base import get_embedder
            from app.vector.base import get_vector_store

            retriever = Retriever(get_db, get_embedder(), get_vector_store())
            return retriever.kb_version()
        except Exception:  # pragma: no cover - defensive
            return 0

    return SemanticCache(
        get_db,
        policy_version_provider=lambda: policy_version,
        kb_version_provider=_kb_version,
    )


router = APIRouter()


@router.get("/cache-stats")
def cache_stats(_: object = Depends(require_api_key)) -> dict:
    """Hit/miss counters, savings, versions and tuning values."""
    stats = _cache().stats()
    stats["threshold"] = settings.cache_similarity_threshold
    stats["ttl_seconds"] = settings.cache_ttl_seconds
    return stats
