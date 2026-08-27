"""Deterministic feature-hashing embeddings (DECISIONS B9 / D5).

256-dim vectors built from ``hashlib.sha256`` over character 3-grams and
word tokens, sign hashing, L2-normalized.

NEVER uses the builtin ``hash()`` (it is salted per process, which would
break determinism and persistence of the semantic cache). Identical inputs
produce identical vectors across processes and restarts.

``cosine_similarity`` is exported here and re-exported from the
``app.providers.embeddings`` package.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable

from app.providers.embeddings.base import Embedder

__all__ = ["EMBEDDING_DIM", "MockEmbedder", "cosine_similarity", "embed_text"]

#: Fixed embedding dimensionality (must match the pgvector ``vector(256)`` DDL).
EMBEDDING_DIM = 256

_WS_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[a-z0-9]+")


def normalize_text(text: str) -> str:
    """Lowercase, strip and collapse internal whitespace."""
    return _WS_RE.sub(" ", (text or "").strip().lower())


def _features(text: str) -> list[str]:
    """Character 3-grams plus word tokens of the normalized text."""
    norm = normalize_text(text)
    words = _WORD_RE.findall(norm)
    grams = [norm[i : i + 3] for i in range(max(0, len(norm) - 2))]
    return words + grams


def embed_text(text: str) -> list[float]:
    """Deterministically embed one text into an L2-normalized 256-dim vector."""
    vector = [0.0] * EMBEDDING_DIM
    for feature in _features(text):
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0.0:
        return vector  # empty/whitespace-only text -> zero vector
    return [value / norm for value in vector]


def cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    """Cosine similarity between two vectors (robust to zero vectors)."""
    va = list(a)
    vb = list(b)
    if len(va) != len(vb):
        raise ValueError(f"vectors must have equal length ({len(va)} != {len(vb)})")
    dot = sum(x * y for x, y in zip(va, vb, strict=False))
    norm_a = math.sqrt(sum(x * x for x in va))
    norm_b = math.sqrt(sum(y * y for y in vb))
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class MockEmbedder(Embedder):
    """Deterministic, dependency-free embedder (default MVP path)."""

    provider_name = "mock"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [embed_text(text) for text in texts]
