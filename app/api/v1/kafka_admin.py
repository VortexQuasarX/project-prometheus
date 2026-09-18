"""Kafka Admin & Telemetry REST endpoints.

Provides real-time visibility into Kafka broker connectivity, topic partitions,
and live event publishing throughput for enterprise event streaming.
"""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import require_api_key
from app.events_pipeline.kafka_pipeline import (
    TOPIC_AUDIT,
    TOPIC_COSTS,
    TOPIC_DLQ,
    TOPIC_REQUESTS,
    get_kafka_telemetry_status,
    publish_telemetry_event,
)

router = APIRouter(prefix="/kafka", tags=["kafka"])


class TestProduceRequest(BaseModel):
    topic: str = TOPIC_REQUESTS
    message: dict[str, Any] = {"test": True, "source": "admin_probe"}


@router.get("/status")
def kafka_status(_: Any = Depends(require_api_key)) -> dict[str, Any]:
    """Retrieve runtime Kafka broker connection, topic partitions, and throughput."""
    return get_kafka_telemetry_status()


@router.get("/topics")
def kafka_topics(_: Any = Depends(require_api_key)) -> dict[str, Any]:
    """List managed Kafka topics and their configuration."""
    status = get_kafka_telemetry_status()
    return {
        "broker_type": status["broker_type"],
        "topics": status["topics"],
        "consumer_group": status["consumer_group"],
    }


@router.post("/produce-test")
def kafka_produce_test(req: TestProduceRequest, _: Any = Depends(require_api_key)) -> dict[str, Any]:
    """Publish a test telemetry probe event to the specified topic."""
    t0 = time.perf_counter()
    publish_telemetry_event(req.topic, req.message)
    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "status": "published",
        "topic": req.topic,
        "latency_ms": duration_ms,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
