"""RAG retriever: ingest + retrieve.

Ingest pipeline: chunk -> embed -> vector-store upsert -> Document and
DocumentChunk rows -> kb_version bump (max version over the documents table).

Retrieve pipeline: embed query -> vector search (top_k chunks).

``get_db`` is only required for ingest (Document/DocumentChunk rows are
written there); retrieval works without a database. ``get_db`` may be a
callable returning a SQLAlchemy Session, a ``sessionmaker``, or a
FastAPI-style dependency generator — all are handled.
"""
from __future__ import annotations

import inspect
import logging
from typing import Any, Callable

from app.rag.chunker import chunk_document

logger = logging.getLogger(__name__)

__all__ = ["Retriever"]


def _session_from(get_db: Callable[[], Any]) -> Any:
    """Return a SQLAlchemy Session from any supported get_db shape."""
    db = get_db()
    if inspect.isgenerator(db):
        return next(db)
    try:
        from sqlalchemy.orm import sessionmaker
    except ImportError:  # pragma: no cover - stack mandates SQLAlchemy
        return db
    if isinstance(db, sessionmaker):
        return db()
    return db


class Retriever:
    """Chunk/embed/upsert ingestion and similarity retrieval."""

    def __init__(self, get_db: Callable[[], Any] | None, embedder: Any, vector_store: Any) -> None:
        self._get_db = get_db
        self._embedder = embedder
        self._vector_store = vector_store

    # ------------------------------------------------------------------
    # ingest
    # ------------------------------------------------------------------
    def ingest(
        self,
        document_id: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ingest a document: chunks -> embeddings -> store + DB rows.

        Returns ``{document_id, title, chunks_created, kb_version}`` and
        bumps the global kb_version (max over documents + 1), which the
        semantic cache reads to invalidate stale entries.
        """
        if self._get_db is None:
            raise ValueError(
                "Retriever.ingest requires a get_db callable (Document and "
                "DocumentChunk rows are written there)."
            )
        chunks = chunk_document(document_id, title, content, metadata)
        embeddings = (
            self._embedder.embed([chunk["content"] for chunk in chunks]) if chunks else []
        )
        for chunk, embedding in zip(chunks, embeddings, strict=False):
            self._vector_store.upsert(
                chunk["document_id"],
                chunk["chunk_id"],
                chunk["content"],
                embedding,
                metadata=chunk["metadata"],
            )

        session = _session_from(self._get_db)
        try:
            from app.db.models import Document, DocumentChunk

            new_version = self._max_kb_version(session) + 1
            document = session.query(Document).filter_by(document_id=document_id).first()
            if document is None:
                document = Document(
                    document_id=document_id,
                    title=title,
                    source=metadata.get("source") if isinstance(metadata, dict) else None,
                    details=dict(metadata or {}),
                    kb_version=new_version,
                )
                session.add(document)
            else:
                document.title = title
                document.details = dict(metadata or {})
                document.kb_version = new_version
            session.flush()
            session.query(DocumentChunk).filter_by(document_id=document_id).delete()
            for chunk in chunks:
                session.add(
                    DocumentChunk(
                        chunk_id=chunk["chunk_id"],
                        document_id=document_id,
                        index=chunk["index"],
                        content=chunk["content"],
                        token_count=chunk["token_count"],
                        details=chunk["metadata"],
                    )
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        return {
            "document_id": document_id,
            "title": title,
            "chunks_created": len(chunks),
            "kb_version": new_version,
        }

    def _max_kb_version(self, session: Any) -> int:
        from sqlalchemy import func

        from app.db.models import Document

        value = session.query(func.max(Document.kb_version)).scalar()
        return int(value or 0)

    # ------------------------------------------------------------------
    # retrieval
    # ------------------------------------------------------------------
    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Embed the query and return the top_k nearest chunks."""
        embedding = self._embedder.embed([query])[0]
        return self._vector_store.search(embedding, top_k=top_k)

    # ------------------------------------------------------------------
    # versions
    # ------------------------------------------------------------------
    def kb_version(self) -> int:
        """Current global knowledge-base version (max over documents, 0 if none)."""
        if self._get_db is None:
            return 0
        session = _session_from(self._get_db)
        try:
            return self._max_kb_version(session)
        finally:
            session.close()
