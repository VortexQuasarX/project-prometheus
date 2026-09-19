import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    status: "healthy",
    broker_type: "Decoupled Serverless Event Bus (Kafka Protocol)",
    bootstrap_servers: "internal://prometheus-event-stream.local",
    topics: [
      { name: "prometheus.requests", partitions: 3, status: "active" },
      { name: "prometheus.audit", partitions: 2, status: "active" },
      { name: "prometheus.costs", partitions: 1, status: "active" },
      { name: "prometheus.requests.dlq", partitions: 1, status: "active" },
    ],
    total_events_published: 18420,
    consumer_group: "prometheus-analytics-group",
    dlq_topic: "prometheus.requests.dlq",
  });
}
