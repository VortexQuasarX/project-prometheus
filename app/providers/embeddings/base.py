"""Embedding provider abstraction (fixed contract).

    Embedder.embed(texts: list[str]) -> list[list[float]]
    get_embedder() -> Embedder          # selects by settings.embedding_provider

Vectors are L2-normalized so cosine similarity equals the dot product.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

__all__ = ["Embedder", "SUPPORTED_EMBEDDING_PROVIDERS", "get_embedder"]

SUPPORTED_EMBEDDING_PROVIDERS = ("mock", "bedrock", "openai")


class Embedder(ABC):
    """Interface every embedding backend implements."""

    provider_name: str = "base"

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into L2-normalized vectors."""
        raise NotImplementedError


def get_embedder() -> Embedder:
    """Factory: return the embedder selected by ``settings.embedding_provider``.

    ``mock`` (default, deterministic feature hashing, no AWS) or ``bedrock``
    (Amazon Titan via boto3, production path).
    """
    from app.providers import get_setting

    provider = (
        get_setting("embedding_provider", "mock") or "mock"
    ).strip().lower()
    if provider == "mock":
        from app.providers.embeddings.mock_embeddings import MockEmbedder

        return MockEmbedder()
    if provider == "bedrock":
        from app.providers.embeddings.bedrock_embeddings import BedrockEmbedder

        return BedrockEmbedder()
    if provider == "openai":
        from app.providers.embeddings.openai_embeddings import OpenAIEmbedder

        return OpenAIEmbedder()
    raise ValueError(
        f"Unknown embedding provider {provider!r}; expected one of {SUPPORTED_EMBEDDING_PROVIDERS}"
    )
