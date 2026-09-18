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
from collections.abc import Callable
from typing import Any

from app.rag.bm25 import BM25Index
from app.rag.chunker import chunk_document
from app.rag.reranker import CrossEncoderReRanker

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
        self._bm25 = BM25Index()
        self._reranker = CrossEncoderReRanker()
        self._bm25_initialized = False

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
            self._bm25_initialized = False
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

    def _ensure_bm25_indexed(self) -> None:
        """Ensure the BM25 index is populated with chunks from database or vector store."""
        if self._bm25_initialized:
            return
        chunks: list[dict[str, Any]] = []
        if self._get_db is not None:
            try:
                session = _session_from(self._get_db)
                from app.db.models import Document, DocumentChunk

                rows = (
                    session.query(DocumentChunk, Document.title)
                    .join(Document, DocumentChunk.document_id == Document.document_id)
                    .all()
                )
                for chunk_row, doc_title in rows:
                    chunks.append(
                        {
                            "chunk_id": chunk_row.chunk_id,
                            "document_id": chunk_row.document_id,
                            "content": chunk_row.content,
                            "title": doc_title or "",
                            "metadata": dict(chunk_row.details or {}),
                        }
                    )
                session.close()
            except Exception as e:
                logger.debug("Could not query DB chunks for BM25: %s", e)

        # Fallback to local vector store entries if DB yielded nothing
        if not chunks and hasattr(self._vector_store, "_entries") and self._vector_store._entries:
            for entry in self._vector_store._entries:
                chunks.append(
                    {
                        "chunk_id": entry.get("chunk_id", ""),
                        "document_id": entry.get("document_id", ""),
                        "content": entry.get("content", ""),
                        "title": entry.get("metadata", {}).get("title", ""),
                        "metadata": dict(entry.get("metadata") or {}),
                    }
                )

        if chunks:
            self._bm25.fit(chunks)
        self._bm25_initialized = True

    # ------------------------------------------------------------------
    # retrieval (Dense, Sparse BM25, and Hybrid RRF + Cross-Encoder)
    # ------------------------------------------------------------------
    def retrieve(self, query: str, top_k: int = 5, mode: str = "hybrid") -> list[dict[str, Any]]:
        """Retrieve top_k chunks using dense, sparse (BM25), or hybrid RRF + Cross-Encoder re-ranking."""
        if not query or not query.strip():
            return []

        # 1. Pure Dense Mode
        if mode == "dense":
            embedding = self._embedder.embed([query])[0]
            return self._vector_store.search(embedding, top_k=top_k)

        self._ensure_bm25_indexed()

        # 2. Pure Sparse Mode (BM25)
        if mode == "sparse":
            bm25_results = self._bm25.search(query, top_k=top_k)
            return [
                {
                    "document_id": chunk.get("document_id", ""),
                    "chunk_id": chunk.get("chunk_id", ""),
                    "content": chunk.get("content", ""),
                    "score": round(score, 4),
                    "bm25_score": round(score, 4),
                    "metadata": chunk.get("metadata", {}),
                }
                for chunk, score in bm25_results
            ]

        # 3. Hybrid Search (Dense + BM25) with Reciprocal Rank Fusion (RRF) & Cross-Encoder
        dense_k = max(10, top_k * 2)
        embedding = self._embedder.embed([query])[0]
        dense_results = self._vector_store.search(embedding, top_k=dense_k)
        bm25_results = self._bm25.search(query, top_k=dense_k)

        # Build candidate pool mapping chunk_id -> dict
        candidates: dict[str, dict[str, Any]] = {}
        rrf_scores: dict[str, float] = {}

        # Dense ranking contribution: 1 / (60 + rank)
        for rank, item in enumerate(dense_results):
            cid = item["chunk_id"]
            candidates[cid] = dict(item)
            candidates[cid]["dense_score"] = round(float(item.get("score", 0.0)), 4)
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (60.0 + rank))

        # BM25 ranking contribution: 1 / (60 + rank)
        for rank, (chunk, score) in enumerate(bm25_results):
            cid = chunk.get("chunk_id", "")
            if not cid:
                continue
            if cid not in candidates:
                candidates[cid] = {
                    "document_id": chunk.get("document_id", ""),
                    "chunk_id": cid,
                    "content": chunk.get("content", ""),
                    "metadata": chunk.get("metadata", {}),
                }
            candidates[cid]["bm25_score"] = round(float(score), 4)
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (60.0 + rank))

        # Attach RRF score
        for cid, cand in candidates.items():
            cand["rrf_score"] = round(rrf_scores.get(cid, 0.0), 5)

        candidate_list = list(candidates.values())
        if not candidate_list:
            return []

        # Re-rank candidate pool using Cross-Encoder
        reranked = self._reranker.rerank(query, candidate_list, top_k=top_k)
        for item in reranked:
            item["score"] = item.get("rerank_score", item.get("dense_score", 0.0))
            item["retrieval_mode"] = "hybrid"

        return reranked

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
