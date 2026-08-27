"""Vector store abstraction (fixed contract).

    VectorStore.upsert(document_id, chunk_id, content, embedding, metadata=None)
    VectorStore.search(embedding, top_k=5) -> list[dict]
        # each dict: {document_id, chunk_id, content, score, metadata}
    VectorStore.delete_document(document_id)
    VectorStore.count() -> int

``get_vector_store()`` selects by ``settings.vector_store_provider``:
``local`` (in-memory + JSONL, no database — the MVP default) or ``pgvector``
(prepared Aurora path, inert unless explicitly selected).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

__all__ = ["VectorStore", "get_vector_store"]


class VectorStore(ABC):
    """Interface every vector store backend implements."""

    provider_name: str = "base"

    @abstractmethod
    def upsert(
        self,
        document_id: str,
        chunk_id: str,
        content: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Insert or replace the chunk identified by (document_id, chunk_id)."""
        raise NotImplementedError

    @abstractmethod
    def search(self, embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        """Return the top_k nearest chunks: {document_id, chunk_id, content, score, metadata}."""
        raise NotImplementedError

    @abstractmethod
    def delete_document(self, document_id: str) -> None:
        """Delete every chunk belonging to a document."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Number of stored chunks."""
        raise NotImplementedError


def get_vector_store() -> VectorStore:
    """Factory: return the vector store selected by settings.vector_store_provider."""
    from app.providers import get_setting

    provider = (
        get_setting("vector_store_provider", "local") or "local"
    ).strip().lower()
    if provider == "local":
        from app.vector.local_vector_store import LocalVectorStore

        return LocalVectorStore()
    if provider == "pgvector":
        from app.vector.pgvector_store import PgVectorStore

        return PgVectorStore()
    raise ValueError(
        f"Unknown vector store provider {provider!r}; expected 'local' or 'pgvector'"
    )
