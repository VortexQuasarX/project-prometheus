"""Semantic cache: similarity matching, versioning, TTL, hit/miss stats."""
from __future__ import annotations

from app.cache.cache_policy import should_cache
from app.cache.semantic_cache import SemanticCache

__all__ = ["SemanticCache", "should_cache"]
