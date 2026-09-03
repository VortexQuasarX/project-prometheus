"""DB-backed semantic cache (DECISIONS B10).

Contract (fixed):

    SemanticCache(get_db, policy_version_provider, kb_version_provider)
        .lookup(query, embedding) -> dict | None
        .put(query, embedding, answer, model, input_tokens, output_tokens,
             estimated_cost_usd) -> None
        .stats() -> dict
        .invalidate() -> None

Matching: cosine similarity against non-expired entries whose stored
``policy_version`` / ``kb_version`` / ``cache_version`` equal the CURRENT
versions (read from the injected providers); hit iff the best cosine is
>= ``settings.cache_similarity_threshold`` (default 0.82). Entries expire
after ``settings.cache_ttl_seconds`` (default 3600).

Persistence: one ``cache_entries`` row per entry plus two reserved meta rows
(no extra model ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â the 19-table contract is fixed):

- ``__stats__``   holds hit_count / miss_count / total_cost_saved_usd as a
                  JSON payload in the row's ``query_text`` column
- ``__version__`` holds the cache_version in the row's ``cache_version``
                  column (bumped by :meth:`invalidate`)

``get_db`` may be a callable returning a SQLAlchemy Session, a
``sessionmaker``, or a FastAPI-style dependency generator ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â all are handled.
Timestamps are stored as UTC ISO-8601 strings.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.providers import get_setting
from app.providers.embeddings.mock_embeddings import cosine_similarity

logger = logging.getLogger(__name__)

__all__ = ["SemanticCache", "normalize_query", "STATS_ROW_KEY", "VERSION_ROW_KEY"]

#: Reserved cache_key prefix for internal meta rows (never matched, never counted).
CACHE_KEY_PREFIX = "__"
STATS_ROW_KEY = "__stats__"
VERSION_ROW_KEY = "__version__"

#: Fallback cache-read rate ($/1k tokens) when app.cost.pricing is unavailable.
DEFAULT_CACHE_READ_RATE_PER_1K = 0.001


def normalize_query(query: str) -> str:
    """Lowercase, strip and collapse whitespace (cache-key normalization)."""
    return " ".join((query or "").strip().lower().split())


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _from_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except ValueError:
        return None


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


def _cache_entry_model() -> Any:
    from app.db.models import CacheEntry

    return CacheEntry


class SemanticCache:
    """Version-aware semantic cache over the ``cache_entries`` table."""

    def __init__(
        self,
        get_db: Callable[[], Any],
        policy_version_provider: Callable[[], int] | None = None,
        kb_version_provider: Callable[[], int] | None = None,
    ) -> None:
        self._get_db = get_db
        self._policy_version_provider = policy_version_provider or (lambda: 0)
        self._kb_version_provider = kb_version_provider or (lambda: 0)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def lookup(self, query: str, embedding: list[float]) -> dict[str, Any] | None:
        """Return the best matching entry dict or None.

        Entry dict keys (contract): answer, model, input_tokens,
        output_tokens, estimated_cost_usd, cost_saved_usd, hit_count,
        created_at ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â plus ``similarity`` as a documented extra. A lookup that
        does not hit counts as a miss (persisted).
        """
        policy_version, kb_version, cache_version = self._versions()
        threshold = self._threshold()
        session = self._session()
        try:
            self._ensure_meta(session)
            self._sweep(session, policy_version, kb_version, cache_version)
            now = _now()
            best: tuple[float, Any] | None = None
            model = _cache_entry_model()
            rows = (
                session.query(model)
                .filter(~model.cache_key.in_((STATS_ROW_KEY, VERSION_ROW_KEY)))
                .all()
            )
            for row in rows:
                expires = _from_iso(row.expires_at)
                if expires is not None and expires <= now:
                    continue
                if (
                    int(row.policy_version or 0) != policy_version
                    or int(row.kb_version or 0) != kb_version
                    or int(row.cache_version or 0) != cache_version
                ):
                    continue
                similarity = cosine_similarity(embedding, row.embedding or [])
                if best is None or similarity > best[0]:
                    best = (similarity, row)

            if best is None or best[0] < threshold:
                self._record_miss(session)
                session.commit()
                return None

            row = best[1]
            row.hit_count = int(row.hit_count or 0) + 1
            row.last_hit_at = _now()
            cost_saved = self._estimate_cost_saved(row)
            payload = self._stats_payload(session)
            payload["hit_count"] += 1
            payload["total_cost_saved_usd"] = round(
                payload["total_cost_saved_usd"] + cost_saved, 6
            )
            self._save_stats(session, payload)
            session.commit()
            return {
                "answer": row.answer,
                "model": row.model,
                "input_tokens": int(row.input_tokens or 0),
                "output_tokens": int(row.output_tokens or 0),
                "estimated_cost_usd": float(row.estimated_cost_usd or 0.0),
                "cost_saved_usd": round(cost_saved, 6),
                "hit_count": int(row.hit_count),
                "created_at": row.created_at or "",
                "similarity": best[0],
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def put(
        self,
        query: str,
        embedding: list[float],
        answer: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        estimated_cost_usd: float,
    ) -> None:
        """Store an answer with TTL expiry and the current version stamps.

        The pipeline should only call this after ``cache_policy.should_cache``
        returned True (never cache refusals/blocked responses).
        """
        policy_version, kb_version, cache_version = self._versions()
        ttl = self._ttl_seconds()
        session = self._session()
        try:
            self._ensure_meta(session)
            self._sweep(session, policy_version, kb_version, cache_version)
            model_cls = _cache_entry_model()
            normalized = normalize_query(query)
            storage_key = hashlib.sha256(
                f"{normalized}|{policy_version}|{kb_version}|{cache_version}".encode()
            ).hexdigest()
            session.query(model_cls).filter_by(cache_key=storage_key).delete()
            entry = model_cls(
                cache_key=storage_key,
                query_text=normalized,
                embedding=[float(value) for value in embedding],
                model=model,
                answer=answer,
                input_tokens=max(0, int(input_tokens or 0)),
                output_tokens=max(0, int(output_tokens or 0)),
                estimated_cost_usd=float(estimated_cost_usd or 0.0),
                policy_version=policy_version,
                kb_version=kb_version,
                cache_version=cache_version,
                hit_count=0,
                created_at=_now(),
                expires_at=_now() + timedelta(seconds=ttl),
                last_hit_at=None,
            )
            session.add(entry)
            try:
                from sqlalchemy.exc import IntegrityError
                session.commit()
            except IntegrityError:
                session.rollback()
                logger.debug("Cache entry %s inserted concurrently", storage_key)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def stats(self) -> dict[str, Any]:
        """Persisted hit/miss counters, savings, versions and tuning values."""
        policy_version, kb_version, cache_version = self._versions()
        session = self._session()
        try:
            self._ensure_meta(session)
            self._sweep(session, policy_version, kb_version, cache_version)
            model_cls = _cache_entry_model()
            entry_count = (
                session.query(model_cls)
                .filter(~model_cls.cache_key.in_((STATS_ROW_KEY, VERSION_ROW_KEY)))
                .count()
            )
            payload = self._stats_payload(session)
            hits = int(payload["hit_count"])
            misses = int(payload["miss_count"])
            total = hits + misses
            hit_rate = round(hits / total, 4) if total else 0.0
            session.commit()
            return {
                "hit_count": hits,
                "miss_count": misses,
                "hit_rate": hit_rate,
                "entry_count": entry_count,
                "total_cost_saved_usd": round(float(payload["total_cost_saved_usd"]), 6),
                "threshold": self._threshold(),
                "ttl_seconds": self._ttl_seconds(),
                "policy_version": policy_version,
                "kb_version": kb_version,
                "cache_version": cache_version,
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def invalidate(self) -> int:
        """Bump cache_version and drop every real entry (simplest consistent wipe).

        Returns the new cache_version.
        """
        session = self._session()
        try:
            self._ensure_meta(session)
            model_cls = _cache_entry_model()
            session.query(model_cls).filter(
                ~model_cls.cache_key.in_((STATS_ROW_KEY, VERSION_ROW_KEY))
            ).delete(synchronize_session=False)
            version_row = session.query(model_cls).filter_by(cache_key=VERSION_ROW_KEY).first()
            version_row.cache_version = int(version_row.cache_version or 0) + 1
            stats_row = session.query(model_cls).filter_by(cache_key=STATS_ROW_KEY).first()
            stats_row.query_text = json.dumps(
                {"hit_count": 0, "miss_count": 0, "total_cost_saved_usd": 0.0}
            )
            session.commit()
            return int(version_row.cache_version)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _session(self) -> Any:
        return _session_from(self._get_db)

    def _versions(self) -> tuple[int, int, int]:
        return (
            self._safe_version(self._policy_version_provider),
            self._safe_version(self._kb_version_provider),
            self._read_cache_version(),
        )

    @staticmethod
    def _safe_version(provider: Callable[[], int]) -> int:
        try:
            return max(0, int(provider() or 0))
        except Exception:  # noqa: BLE001 - provider failure degrades to version 0
            logger.warning("version provider failed; treating version as 0", exc_info=True)
            return 0

    def _read_cache_version(self) -> int:
        session = self._session()
        try:
            row = (
                session.query(_cache_entry_model())
                .filter_by(cache_key=VERSION_ROW_KEY)
                .first()
            )
            return int(row.cache_version or 0) if row is not None else 0
        finally:
            session.close()

    def _ensure_meta(self, session: Any) -> None:
        model_cls = _cache_entry_model()
        now = _now()
        stats = session.query(model_cls).filter_by(cache_key=STATS_ROW_KEY).first()
        if stats is None:
            session.add(
                model_cls(
                    cache_key=STATS_ROW_KEY,
                    query_text=json.dumps(
                        {"hit_count": 0, "miss_count": 0, "total_cost_saved_usd": 0.0}
                    ),
                    embedding=None,
                    model="",
                    answer="",
                    input_tokens=0,
                    output_tokens=0,
                    estimated_cost_usd=0.0,
                    policy_version=0,
                    kb_version=0,
                    cache_version=0,
                    hit_count=0,
                    created_at=now,
                    expires_at=None,
                    last_hit_at=None,
                )
            )
        version = session.query(model_cls).filter_by(cache_key=VERSION_ROW_KEY).first()
        if version is None:
            session.add(
                model_cls(
                    cache_key=VERSION_ROW_KEY,
                    query_text="",
                    embedding=None,
                    model="",
                    answer="",
                    input_tokens=0,
                    output_tokens=0,
                    estimated_cost_usd=0.0,
                    policy_version=0,
                    kb_version=0,
                    cache_version=0,
                    hit_count=0,
                    created_at=now,
                    expires_at=None,
                    last_hit_at=None,
                )
            )
        session.flush()  # autoflush=False: make the meta rows visible to later queries

    def _stats_payload(self, session: Any) -> dict[str, Any]:
        row = (
            session.query(_cache_entry_model())
            .filter_by(cache_key=STATS_ROW_KEY)
            .first()
        )
        if row is None or not row.query_text:
            return {"hit_count": 0, "miss_count": 0, "total_cost_saved_usd": 0.0}
        try:
            payload = json.loads(row.query_text)
            return {
                "hit_count": int(payload.get("hit_count", 0)),
                "miss_count": int(payload.get("miss_count", 0)),
                "total_cost_saved_usd": float(payload.get("total_cost_saved_usd", 0.0)),
            }
        except (TypeError, ValueError, json.JSONDecodeError):
            return {"hit_count": 0, "miss_count": 0, "total_cost_saved_usd": 0.0}

    def _save_stats(self, session: Any, payload: dict[str, Any]) -> None:
        row = (
            session.query(_cache_entry_model())
            .filter_by(cache_key=STATS_ROW_KEY)
            .first()
        )
        if row is None:
            self._ensure_meta(session)
            row = (
                session.query(_cache_entry_model())
                .filter_by(cache_key=STATS_ROW_KEY)
                .first()
            )
        row.query_text = json.dumps(payload)

    def _record_miss(self, session: Any) -> None:
        payload = self._stats_payload(session)
        payload["miss_count"] += 1
        self._save_stats(session, payload)

    def _sweep(
        self,
        session: Any,
        policy_version: int,
        kb_version: int,
        cache_version: int,
    ) -> None:
        """Delete expired or version-stale real entries (lazy expiry)."""
        model_cls = _cache_entry_model()
        now = _now()
        rows = (
            session.query(model_cls)
            .filter(~model_cls.cache_key.in_((STATS_ROW_KEY, VERSION_ROW_KEY)))
            .all()
        )
        for row in rows:
            expires = _from_iso(row.expires_at)
            expired = expires is not None and expires <= now
            stale = (
                int(row.policy_version or 0) != policy_version
                or int(row.kb_version or 0) != kb_version
                or int(row.cache_version or 0) != cache_version
            )
            if expired or stale:
                session.delete(row)

    def _estimate_cost_saved(self, row: Any) -> float:
        """Would-have LLM cost (stored at put time) minus a cache-read leg."""
        would_have = float(row.estimated_cost_usd or 0.0)
        read_rate = self._cache_read_rate_per_1k(row.model)
        read_cost = (int(row.input_tokens or 0) * read_rate) / 1000.0
        return max(0.0, would_have - read_cost)

    @staticmethod
    def _cache_read_rate_per_1k(model: str) -> float:
        """Prefer the project pricing catalog; fall back to the B11 default."""
        try:
            from app.cost.pricing import get_model_pricing

            pricing = get_model_pricing(model)
            rate = pricing.get("cache_read_cost_per_1k_tokens")
            if rate is not None:
                return float(rate)
        except Exception:  # noqa: BLE001 - pricing slice unavailable/renamed
            pass
        return DEFAULT_CACHE_READ_RATE_PER_1K

    @staticmethod
    def _threshold() -> float:
        return max(
            0.0,
            min(1.0, float(get_setting("cache_similarity_threshold", 0.82) or 0.82)),
        )

    @staticmethod
    def _ttl_seconds() -> int:
        return max(0, int(get_setting("cache_ttl_seconds", 3600) or 3600))
