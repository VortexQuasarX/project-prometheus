"""Embedding providers: deterministic mock + Amazon Titan (Bedrock).

``cosine_similarity`` is re-exported here for the semantic cache, vector
stores and retriever (contract).
"""
from __future__ import annotations

from app.providers.embeddings.base import Embedder, get_embedder
from app.providers.embeddings.bedrock_embeddings import BedrockEmbedder
from app.providers.embeddings.mock_embeddings import (
    EMBEDDING_DIM,
    MockEmbedder,
    cosine_similarity,
    embed_text,
    normalize_text,
)

__all__ = [
    "EMBEDDING_DIM",
    "BedrockEmbedder",
    "Embedder",
    "MockEmbedder",
    "cosine_similarity",
    "embed_text",
    "get_embedder",
    "normalize_text",
]
