"""Usage recording and spend aggregation (UTC-day based).

One ``usage_records`` row per LLM call (and per cache hit, with ``cost_usd=0``
and ``cache_saved_usd>0``). Aggregations read the ``date`` column
(``YYYY-MM-DD`` UTC) so daily/monthly rollups are trivial (B19: daily resets
at UTC midnight; monthly = daily rollup).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import func, select

from app.core.logging import get_logger
from app.db.models import UsageRecord, utc_today, utcnow
from app.db.session import SessionLocal

logger = get_logger("prometheus.cost")


def _round(value: float | None) -> float:
    return round(float(value or 0.0), 6)


def record_usage(
    request_id: str,
    model: str,
    provider: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    cost_usd: float = 0.0,
    cache_saved_usd: float = 0.0,
) -> UsageRecord:
    """Persist one usage record (own short-lived session) and return it."""
    with SessionLocal() as session:
        record = UsageRecord(
            request_id=request_id,
            date=utc_today(),
            model=model,
            provider=provider,
            input_tokens=int(input_tokens or 0),
            output_tokens=int(output_tokens or 0),
            cache_read_tokens=int(cache_read_tokens or 0),
            cache_write_tokens=int(cache_write_tokens or 0),
            cost_usd=_round(cost_usd),
            cache_saved_usd=_round(cache_saved_usd),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record


def get_daily_spend() -> float:
    """Total ``cost_usd`` for today (UTC)."""
    with SessionLocal() as session:
        total = session.scalar(
            select(func.coalesce(func.sum(UsageRecord.cost_usd), 0.0)).where(
                UsageRecord.date == utc_today()
            )
        )
        return _round(total)


def get_monthly_spend() -> float:
    """Total ``cost_usd`` for the current UTC month (monthly = daily rollup)."""
    prefix = utc_today()[:7] + "%"
    with SessionLocal() as session:
        total = session.scalar(
            select(func.coalesce(func.sum(UsageRecord.cost_usd), 0.0)).where(
                UsageRecord.date.like(prefix)
            )
        )
        return _round(total)


def get_total_spend() -> float:
    """Lifetime total ``cost_usd`` (dashboard 'total cost' metric)."""
    with SessionLocal() as session:
        total = session.scalar(select(func.coalesce(func.sum(UsageRecord.cost_usd), 0.0)))
        return _round(total)


def get_cache_savings_total() -> float:
    """Total ``cache_saved_usd`` across all usage records."""
    with SessionLocal() as session:
        total = session.scalar(select(func.coalesce(func.sum(UsageRecord.cache_saved_usd), 0.0)))
        return _round(total)


def get_model_wise_spend() -> list[dict[str, Any]]:
    """Per-model rollup: {model, input_tokens, output_tokens, cost_usd, requests}."""
    with SessionLocal() as session:
        rows = session.execute(
            select(
                UsageRecord.model,
                func.coalesce(func.sum(UsageRecord.input_tokens), 0),
                func.coalesce(func.sum(UsageRecord.output_tokens), 0),
                func.coalesce(func.sum(UsageRecord.cost_usd), 0.0),
                func.count(UsageRecord.id),
            ).group_by(UsageRecord.model)
        ).all()
        return [
            {
                "model": row[0],
                "input_tokens": int(row[1]),
                "output_tokens": int(row[2]),
                "cost_usd": _round(row[3]),
                "requests": int(row[4]),
            }
            for row in rows
        ]


def get_usage_stats(days: int = 7) -> dict[str, Any]:
    """Totals plus a per-day series for the last ``days`` UTC days."""
    days = max(1, int(days))
    today = utc_today()
    start_date = (utcnow().date() - timedelta(days=days - 1)).isoformat()
    with SessionLocal() as session:
        rows = session.execute(
            select(
                UsageRecord.date,
                func.coalesce(func.sum(UsageRecord.cost_usd), 0.0),
                func.coalesce(func.sum(UsageRecord.cache_saved_usd), 0.0),
                func.count(UsageRecord.id),
            )
            .where(UsageRecord.date >= start_date)
            .group_by(UsageRecord.date)
            .order_by(UsageRecord.date.asc())
        ).all()
        totals = session.execute(
            select(
                func.coalesce(func.sum(UsageRecord.cost_usd), 0.0),
                func.coalesce(func.sum(UsageRecord.cache_saved_usd), 0.0),
                func.count(UsageRecord.id),
                func.coalesce(func.sum(UsageRecord.input_tokens), 0),
                func.coalesce(func.sum(UsageRecord.output_tokens), 0),
                func.coalesce(func.sum(UsageRecord.cache_read_tokens), 0),
                func.coalesce(func.sum(UsageRecord.cache_write_tokens), 0),
            ).where(UsageRecord.date >= start_date)
        ).one()

    by_date = {row[0]: row for row in rows}
    daily: list[dict[str, Any]] = []
    for offset in range(days):
        day = (utcnow().date() - timedelta(days=offset)).isoformat()
        row = by_date.get(day)
        daily.append(
            {
                "date": day,
                "cost_usd": _round(row[1]) if row else 0.0,
                "cache_saved_usd": _round(row[2]) if row else 0.0,
                "usage_record_count": int(row[3]) if row else 0,
            }
        )
    daily.reverse()
    return {
        "days": days,
        "start_date": start_date,
        "end_date": today,
        "total_cost_usd": _round(totals[0]),
        "total_cache_savings_usd": _round(totals[1]),
        "usage_record_count": int(totals[2]),
        "total_input_tokens": int(totals[3]),
        "total_output_tokens": int(totals[4]),
        "total_cache_read_tokens": int(totals[5]),
        "total_cache_write_tokens": int(totals[6]),
        "daily": daily,
    }
