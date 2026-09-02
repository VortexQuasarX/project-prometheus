# DATA ENGINEERING

## Event pipeline (Kafka-style; VERIFIED via in-memory broker)

- Producer: `app/events_pipeline/kafka_pipeline.py` — request events
  (`request.completed` with cost/latency/decision) to `prometheus.requests`
- Consumer group `prometheus-analytics`: manual offsets, retries, DLQ
  (`prometheus.requests.dlq`) after 3 failures, block-partition-on-failure
  semantics (VERIFIED: tests/test_events_pipeline.py)
- Live broker connectivity: NOT VERIFIED (no broker on host; docker-compose
  profile `kafka` planned)

## Batch pipeline (PySpark)

`app/spark/pipeline.py` — ingestion → cleaning → transformation → aggregation
→ Parquet output. **NOT VERIFIED: no JVM on the host.** Largest verified
workload: none (the dataset builder operates in-process).

## Airflow

`ml/airflow_dags/prometheus_dag.py` — ingest → validate → transform →
features → train → evaluate → register → deploy with retries and
dependencies. **Scheduler execution NOT VERIFIED on Windows** (DAG-structure
checked by import).

## Data warehouse shape (Parquet)

Events land as JSON; the Spark job flattens them into
`events/date=/model=/` partitions for cost analytics and drift reference
windows.
