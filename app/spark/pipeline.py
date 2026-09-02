"""PySpark batch pipeline for Prometheus events (NOT VERIFIED: no JVM on host).

Reads JSON event exports, cleans, aggregates cost/latency per model per day,
writes Parquet partitioned by date. Execute with:
    spark-submit --jars packages app/spark/pipeline.py
(Requires Java 17 + Apache Spark 3.5.)
"""
from __future__ import annotations

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

INPUT_PATH = "data/events/*.json"
OUTPUT_PATH = "data/warehouse/usage"


def build_session() -> SparkSession:
    return (
        SparkSession.builder.appName("prometheus-events")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def run(spark: SparkSession | None = None) -> None:
    spark = spark or build_session()
    df = spark.read.json(INPUT_PATH)

    cleaned = (
        df.filter(F.col("request_id").isNotNull())
        .dropDuplicates(["request_id"])
        .withColumn("date", F.to_date("ts"))
        .withColumn("cost_usd", F.col("cost_usd").cast("double").fillna(0.0))
    )

    agg = (
        cleaned.groupBy("date", "model")
        .agg(
            F.count("*").alias("requests"),
            F.sum("cost_usd").alias("cost_usd"),
            F.sum(F.when(F.col("cache_hit"), 1).otherwise(0)).alias("cache_hits"),
            F.avg("latency_ms").alias("avg_latency_ms"),
            F.expr("percentile_approx(latency_ms, 0.95)").alias("p95_latency_ms"),
        )
    )

    (cleaned.write.mode("overwrite").partitionBy("date").parquet(f"{OUTPUT_PATH}/events"))
    (agg.write.mode("overwrite").partitionBy("date").parquet(f"{OUTPUT_PATH}/daily_model_usage"))


if __name__ == "__main__":
    run()
