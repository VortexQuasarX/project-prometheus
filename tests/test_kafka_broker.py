"""Unit tests for the KafkaBroker adapter (no live broker required).

Uses a stateful fake KafkaConsumer that models group join, seek, manual
offset commits, and poll-from-position. Live-broker behavior (produce, group
consume, commit, retry, DLQ) was verified against a real broker on
2026-09-05; this suite pins the adapter's semantics for CI.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.events_pipeline.kafka_pipeline import InMemoryBroker, KafkaBroker, make_broker  # noqa: E402


class FakeTopicPartition:
    def __init__(self, topic: str, partition: int) -> None:
        self.topic = topic
        self.partition = partition


class FakeOffsetAndMetadata:
    def __init__(self, offset: int, metadata: str, leader_epoch: int = -1) -> None:
        self.offset = offset
        self.metadata = metadata
        self.leader_epoch = leader_epoch


class FakeConsumer:
    """Stateful stand-in: first poll joins the group (no records)."""

    def __init__(self, records: list) -> None:
        self.records = records
        self.tp = FakeTopicPartition("t", 0)
        self.assigned = False
        self.position = 0
        self.committed_offset: int | None = None
        self.seeks: list[int] = []
        self.commit_calls: list[dict] = []
        self.poll_calls = 0

    def assignment(self) -> set:
        return {self.tp} if self.assigned else set()

    def committed(self, tp) -> int | None:  # noqa: ANN001
        return self.committed_offset

    def seek(self, tp, offset: int) -> None:  # noqa: ANN001
        self.seeks.append(offset)
        self.position = offset

    def seek_to_beginning(self, tp) -> None:  # noqa: ANN001
        self.seeks.append(0)
        self.position = 0

    def poll(self, timeout_ms: int = 0, max_records: int = 500) -> dict:  # noqa: ANN001
        self.poll_calls += 1
        if not self.assigned:
            self.assigned = True
            return {self.tp: []}
        if self.position >= len(self.records):
            return {self.tp: []}
        batch = self.records[self.position : self.position + max_records]
        self.position += len(batch)
        return {self.tp: batch}

    def commit(self, offsets: dict | None = None) -> None:  # noqa: ANN001
        self.commit_calls.append(offsets)


def _records(n: int) -> list:
    out = []
    for i in range(n):
        r = FakeTopicPartition("t", 0)  # placeholder replaced below
        del r
        rec = type("R", (), {})()
        rec.offset = i
        rec.value = {"request_id": f"r{i}"}
        rec.topic = "t"
        rec.partition = 0
        out.append(rec)
    return out


def test_make_broker_factory() -> None:
    assert isinstance(make_broker(""), InMemoryBroker)
    with patch("kafka.KafkaProducer"):
        assert isinstance(make_broker("localhost:9092"), KafkaBroker)


def test_kafka_broker_consume_commit_roundtrip() -> None:
    records = _records(3)
    with patch("kafka.KafkaProducer"), patch("kafka.KafkaConsumer", return_value=FakeConsumer(records)):
        broker = KafkaBroker("localhost:9092")
        broker.send("t", {"x": 1})
        assert broker._producer.send.called

        out = broker.consume("t", "g", count=10)
        assert [r["value"]["request_id"] for r in out] == ["r0", "r1", "r2"]
        assert [r["_offset"] for r in out] == [0, 1, 2]

        broker.commit("t", "g", 3)
        assert len(broker._consumers[("t", "g")].commit_calls) == 1
        offsets = broker._consumers[("t", "g")].commit_calls[0]
        for om in offsets.values():
            assert om.offset == 3

        broker._consumers[("t", "g")].committed_offset = 3
        out2 = broker.consume("t", "g", count=10)
        assert out2 == []
        assert broker._consumers[("t", "g")].seeks[-1] == 3


def test_kafka_broker_redelivers_uncommitted() -> None:
    records = _records(1)
    with patch("kafka.KafkaProducer"), patch("kafka.KafkaConsumer", return_value=FakeConsumer(records)):
        broker = KafkaBroker("localhost:9092")
        out1 = broker.consume("t", "g", count=10)
        assert len(out1) == 1 and out1[0]["_offset"] == 0
        assert broker._consumers[("t", "g")].commit_calls == []

        # no commit happened -> the same record is re-delivered (retry semantics)
        out2 = broker.consume("t", "g", count=10)
        assert len(out2) == 1 and out2[0]["_offset"] == 0
