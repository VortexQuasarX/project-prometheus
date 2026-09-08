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
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

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
    "KafkaBroker",
    "make_broker",
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


class KafkaBroker:
    """Real Kafka adapter with the same protocol as InMemoryBroker.

    Active when ``settings.kafka_bootstrap_servers`` is configured. One
    long-lived consumer per (topic, group); every ``consume`` re-seeks to the
    group's committed offset so failed batches are re-delivered (the pipeline
    relies on this for retries). Single-partition assumption matches the
    compose broker (num.partitions=1).
    """

    def __init__(self, bootstrap_servers: str) -> None:
        from kafka import KafkaProducer

        self._bs = bootstrap_servers
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            linger_ms=0,
        )
        self._consumers: dict[tuple[str, str], Any] = {}
        self._buffer: dict[tuple[str, str], list[dict[str, Any]]] = {}

    def send(self, topic: str, value: dict[str, Any]) -> None:
        self._producer.send(topic, value=value)
        self._producer.flush(timeout=10)

    def _consumer(self, topic: str, group: str) -> Any:
        from kafka import KafkaConsumer

        key = (topic, group)
        if key not in self._consumers:
            self._consumers[key] = KafkaConsumer(
                topic,
                bootstrap_servers=self._bs,
                group_id=group,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                consumer_timeout_ms=2000,
                value_deserializer=lambda b: json.loads(b.decode("utf-8")),
            )
        return self._consumers[key]

    def consume(self, topic: str, group: str, count: int = 1) -> list[dict[str, Any]]:
        key = (topic, group)
        consumer = self._consumer(topic, group)
        # First poll completes the group join; without it assignment() is
        # empty and every subsequent seek/poll is a no-op. Warm-up records
        # are discarded - the seek below re-reads them deterministically.
        deadline = time.time() + 20
        while not consumer.assignment() and time.time() < deadline:
            consumer.poll(timeout_ms=1000, max_records=max(count, 1))
        # Restart from the group's committed offset on every batch so that a
        # failed (uncommitted) record is re-delivered - mirrors InMemoryBroker.
        for tp in consumer.assignment():
            committed = consumer.committed(tp)
            if committed is not None:
                consumer.seek(tp, committed)
            else:
                consumer.seek_to_beginning(tp)
        out: list[dict[str, Any]] = list(self._buffer.get(key, []))
        self._buffer[key] = []
        while len(out) < count:
            batch = consumer.poll(timeout_ms=2000, max_records=count - len(out))
            if not batch or not any(batch.values()):
                break
            for records in batch.values():
                for r in records:
                    rec = {
                        "value": r.value,
                        "_offset": r.offset,
                        "_tp": r.topic,
                        "_partition": r.partition,
                    }
                    if len(out) < count:
                        out.append(rec)
                    else:
                        self._buffer[key].append(rec)
        return out

    def commit(self, topic: str, group: str, offset: int) -> None:

        consumer = self._consumers.get((topic, group))
        if consumer is None or not consumer.assignment():
            return
        from kafka.structs import OffsetAndMetadata

        try:
            offsets = {
                tp: OffsetAndMetadata(offset, "", -1) for tp in consumer.assignment()
            }
        except TypeError:  # kafka-python 2.x signature: (offset, metadata)
            offsets = {tp: OffsetAndMetadata(offset, "") for tp in consumer.assignment()}
        consumer.commit(offsets=offsets)


def make_broker(bootstrap_servers: str = "") -> Any:
    """Factory: real KafkaBroker when servers configured, else in-memory."""
    if bootstrap_servers:
        return KafkaBroker(bootstrap_servers)
    return InMemoryBroker()
