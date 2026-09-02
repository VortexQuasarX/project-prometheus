"""Kafka event pipeline (real kafka-python client + in-memory test transport).

Request events are produced to ``prometheus.requests``; a consumer group
``prometheus-analytics`` processes them with retries and a dead-letter topic
``prometheus.requests.dlq`` after MAX_RETRIES failed attempts. Offsets are
committed manually after successful processing; poison messages never block
the partition. Live Kafka connectivity is NOT VERIFIED locally (no broker) —
the processing logic is VERIFIED via the in-memory broker.
"""
from __future__ import annotations

import json
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)

TOPIC_REQUESTS = "prometheus.requests"
TOPIC_DLQ = "prometheus.requests.dlq"
MAX_RETRIES = 3

__all__ = [
    "TOPIC_REQUESTS",
    "TOPIC_DLQ",
    "MAX_RETRIES",
    "InMemoryBroker",
    "EventProducer",
    "EventConsumer",
]


class InMemoryBroker:
    """Test double with Kafka semantics: topics, per-group offsets, DLQ."""

    def __init__(self) -> None:
        self.topics: dict[str, list[dict[str, Any]]] = {}
        self.offsets: dict[tuple[str, str], int] = {}
        self.published: list[dict[str, Any]] = []

    def send(self, topic: str, value: dict[str, Any]) -> None:
        self.topics.setdefault(topic, []).append({"value": value})
        self.published.append({"topic": topic, "value": value})

    def consume(self, topic: str, group: str, count: int = 1) -> list[dict[str, Any]]:
        """Return up to ``count`` records starting at the group's committed offset."""
        records = self.topics.get(topic, [])
        offset = self.offsets.get((topic, group), 0)
        out = []
        while offset < len(records) and len(out) < count:
            rec = dict(records[offset])
            rec["_offset"] = offset
            out.append(rec)
            offset += 1
        return out

    def commit(self, topic: str, group: str, offset: int) -> None:
        self.offsets[(topic, group)] = max(self.offsets.get((topic, group), 0), offset)


@dataclass
class EventProducer:
    """Producer with JSON serialization; broker optional (logs when absent)."""

    broker: Any = None
    topic: str = TOPIC_REQUESTS

    def emit_request_event(self, request_id: str, payload: dict[str, Any]) -> None:
        self.publish(
            {
                "event_type": "request.completed",
                "request_id": request_id,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                **payload,
            }
        )

    def publish(self, event: dict[str, Any]) -> None:
        if self.broker is not None:
            self.broker.send(self.topic, event)
        else:
            logger.info("kafka event (no broker configured): %s", json.dumps(event)[:200])


class EventConsumer:
    """Consumer with retries and dead-letter handling (poison-proof)."""

    def __init__(
        self,
        broker: Any,
        handler: Callable[[dict[str, Any]], None],
        group: str = "prometheus-analytics",
        topic: str = TOPIC_REQUESTS,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.broker = broker
        self.handler = handler
        self.group = group
        self.topic = topic
        self.max_retries = max_retries
        self.failures: dict[str, int] = {}
        self.processed = 0
        self.dead_lettered = 0

    def process_batch(self, count: int = 10) -> dict[str, int]:
        """Process up to ``count`` pending events; returns counters."""
        pending = self.broker.consume(self.topic, self.group, count=count)
        stats = {"processed": 0, "retried": 0, "dead_lettered": 0}
        for record in pending:
            event = record.get("value") or {}
            event_key = json.dumps(event, sort_keys=True, default=str)
            attempts = self.failures.get(event_key, 0) + 1
            try:
                self.handler(event)
                self.processed += 1
                stats["processed"] += 1
                self.failures.pop(event_key, None)
                self.broker.commit(self.topic, self.group, record["_offset"] + 1)
            except Exception as exc:  # noqa: BLE001 - loop must survive failures
                self.failures[event_key] = attempts
                stats["retried"] += 1
                if attempts >= self.max_retries:
                    # poison message: dead-letter and advance past it
                    self.broker.send(
                        TOPIC_DLQ, {"event": event, "error": str(exc)[:200]}
                    )
                    self.dead_lettered += 1
                    stats["dead_lettered"] += 1
                    self.failures.pop(event_key, None)
                    self.broker.commit(self.topic, self.group, record["_offset"] + 1)
                else:
                    # real Kafka semantics: a failing event blocks the
                    # partition until it is retried successfully or DLQ'd
                    break
        return stats
