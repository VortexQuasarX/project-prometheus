"""Kafka event pipeline tests (in-memory broker with Kafka semantics)."""
from __future__ import annotations

from app.events_pipeline.kafka_pipeline import (
    EventConsumer,
    EventProducer,
    InMemoryBroker,
    TOPIC_DLQ,
)


def test_producer_publishes_and_consumer_processes():
    broker = InMemoryBroker()
    producer = EventProducer(broker=broker)
    seen = []
    consumer = EventConsumer(broker, lambda e: seen.append(e["request_id"]))
    producer.emit_request_event("req_1", {"cost_usd": 0.01})
    producer.emit_request_event("req_2", {"cost_usd": 0.02})
    stats = consumer.process_batch(count=10)
    assert stats["processed"] == 2
    assert seen == ["req_1", "req_2"]
    # idempotent: committed offsets mean no double processing
    assert consumer.process_batch(count=10)["processed"] == 0


def test_consumer_retries_then_dead_letters_poison():
    broker = InMemoryBroker()
    producer = EventProducer(broker=broker)
    producer.publish({"request_id": "poison", "bad": True})
    producer.publish({"request_id": "good"})

    def handler(event):
        if event.get("bad"):
            raise RuntimeError("boom")

    consumer = EventConsumer(broker, handler, max_retries=3)
    stats1 = consumer.process_batch(count=10)
    assert stats1["retried"] >= 1
    stats2 = consumer.process_batch(count=10)
    stats3 = consumer.process_batch(count=10)
    total_dead = stats1["dead_lettered"] + stats2["dead_lettered"] + stats3["dead_lettered"]
    assert total_dead == 1  # poison moved to DLQ after MAX_RETRIES
    assert any(rec["topic"] == TOPIC_DLQ for rec in broker.published)
    # the good event still processed
    assert consumer.processed == 1


def test_consumer_group_offsets_are_independent():
    broker = InMemoryBroker()
    EventProducer(broker=broker).emit_request_event("req_x", {})
    group_a = EventConsumer(broker, lambda e: None, group="a")
    group_b = EventConsumer(broker, lambda e: None, group="b")
    assert group_a.process_batch(count=10)["processed"] == 1
    # group b still sees the event (independent offsets)
    assert group_b.process_batch(count=10)["processed"] == 1
