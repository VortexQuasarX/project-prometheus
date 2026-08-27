"""Aurora pgvector vector store — prepared production path.

Inert unless ``VECTOR_STORE_PROVIDER=pgvector``: constructing it in local
mode raises ``ProviderUnavailableError`` so the app can never accidentally
depend on a database that is not there (spec: "LocalVectorStore must work
without database" — the local store is the default MVP path).

Production DDL (Aurora Serverless v2 PostgreSQL, applied by the infra
slice / migration):

    CREATE EXTENSION IF NOT EXISTS vector;

    -- ``vector(256)`` matches the mock embedding dimension
    -- (app/providers/embeddings/mock_embeddings.py). This class stores the
    -- embedding in a JSON column so it is importable without the pgvector
    -- extension; in production switch the column type to ``vector(256)``
    -- and use the operators below.

    -- HNSW (recommended: high recall at moderate-to-large scale):
    CREATE INDEX document_vectors_hnsw_idx
        ON document_vectors USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);

    -- IVFFlat (cheaper to build; tune ``lists`` to row count, e.g. 100 per
    -- ~100k rows; requires the table to be non-empty):
    CREATE INDEX document_vectors_ivfflat_idx
        ON document_vectors USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);

    -- Production query pattern:
    --   SELECT document_id, chunk_id, content, metadata_json,
    --          1 - (embedding <=> :query) AS score
    --   FROM document_vectors
    --   ORDER BY embedding <=> :query
    --   LIMIT :k;

This implementation computes cosine similarity in Python so it also works
against a plain JSON column; the SQL operator pattern is the documented
production upgrade.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from app.providers import get_setting
from app.providers.embeddings.mock_embeddings import cosine_similarity
from app.providers.llm.base import ProviderUnavailableError
from app.vector.base import VectorStore

logger = logging.getLogger(__name__)

try:  # use the project's declarative base when available (isolated fallback)
    from app.db.base import Base as _DeclarativeBase
except Exception:  # pragma: no cover - keeps this module importable standalone
    from sqlalchemy.orm import declarative_base as _make_declarative_base

    _DeclarativeBase = _make_declarative_base()

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, func  # noqa: E402


class _DocumentVector(_DeclarativeBase):
    """Vector chunk row owned by the pgvector store (not a spec model)."""

    __tablename__ = "document_vectors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(128), nullable=False, index=True)
    chunk_id = Column(String(256), nullable=False, unique=True)
    content = Column(Text, nullable=False)
    # Production: Column(Vector(256)) via `from pgvector.sqlalchemy import Vector`.
    embedding = Column(JSON, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PgVectorStore(VectorStore):
    """Aurora pgvector store; inert unless VECTOR_STORE_PROVIDER=pgvector."""

    provider_name = "pgvector"

    def __init__(self, database_url: str | None = None) -> None:
        provider = (get_setting("vector_store_provider", "local") or "local").strip().lower()
        if provider != "pgvector":
            raise ProviderUnavailableError(
                "PgVectorStore is inert unless VECTOR_STORE_PROVIDER=pgvector; "
                "use the local vector store for the no-database MVP."
            )
        self._database_url = database_url or get_setting("database_url", "") or ""
        if not self._database_url:
            raise ProviderUnavailableError("DATABASE_URL is required for the pgvector store.")
        self._engine: Any = None
        self._session_factory: Any = None
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _ensure_session(self) -> Any:
        with self._lock:
            if self._session_factory is not None:
                return self._session_factory()
            try:
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
            except ImportError as exc:  # pragma: no cover - stack mandates SQLAlchemy
                raise ProviderUnavailableError(
                    "SQLAlchemy is required for the pgvector store."
                ) from exc
            try:
                self._engine = create_engine(self._database_url, pool_pre_ping=True, future=True)
                _DeclarativeBase.metadata.create_all(self._engine)
                self._session_factory = sessionmaker(
                    bind=self._engine, expire_on_commit=False
                )
            except Exception as exc:  # noqa: BLE001 - controlled surface
                raise ProviderUnavailableError(
                    f"Could not connect to the pgvector database: {exc}"
                ) from exc
            return self._session_factory()

    # ------------------------------------------------------------------
    # VectorStore
    # ------------------------------------------------------------------
    def upsert(
        self,
        document_id: str,
        chunk_id: str,
        content: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        session = self._ensure_session()
        try:
            session.query(_DocumentVector).filter_by(chunk_id=chunk_id).delete()
            session.add(
                _DocumentVector(
                    document_id=document_id,
                    chunk_id=chunk_id,
                    content=content,
                    embedding=[float(value) for value in embedding],
                    metadata_json=dict(metadata or {}),
                )
            )
            session.commit()
        except Exception as exc:  # noqa: BLE001 - controlled surface
            session.rollback()
            raise ProviderUnavailableError(f"pgvector upsert failed: {exc}") from exc
        finally:
            session.close()

    def search(self, embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        session = self._ensure_session()
        try:
            rows = session.query(_DocumentVector).all()
            scored = [
                (cosine_similarity(embedding, row.embedding or []), row) for row in rows
            ]
            scored.sort(key=lambda pair: pair[0], reverse=True)
            limit = max(0, int(top_k))
            return [
                {
                    "document_id": row.document_id,
                    "chunk_id": row.chunk_id,
                    "content": row.content,
                    "score": score,
                    "metadata": dict(row.metadata_json or {}),
                }
                for score, row in scored[:limit]
            ]
        except Exception as exc:  # noqa: BLE001 - controlled surface
            raise ProviderUnavailableError(f"pgvector search failed: {exc}") from exc
        finally:
            session.close()

    def delete_document(self, document_id: str) -> None:
        session = self._ensure_session()
        try:
            session.query(_DocumentVector).filter_by(document_id=document_id).delete()
            session.commit()
        except Exception as exc:  # noqa: BLE001 - controlled surface
            session.rollback()
            raise ProviderUnavailableError(f"pgvector delete failed: {exc}") from exc
        finally:
            session.close()

    def count(self) -> int:
        session = self._ensure_session()
        try:
            return int(session.query(func.count(_DocumentVector.id)).scalar() or 0)
        except Exception as exc:  # noqa: BLE001 - controlled surface
            raise ProviderUnavailableError(f"pgvector count failed: {exc}") from exc
        finally:
            session.close()
