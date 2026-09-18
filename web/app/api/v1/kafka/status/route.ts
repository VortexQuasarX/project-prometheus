import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    status: "healthy",
    broker_type: "Apache Kafka KRaft (ap-south-1 Cluster)",
    bootstrap_servers: "b-1.prometheus-kafka.ap-south-1.amazonaws.com:9092",
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
