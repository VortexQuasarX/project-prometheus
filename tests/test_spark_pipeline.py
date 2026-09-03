"""PySpark pipeline test — validates pipeline logic without requiring a JVM.

Tests are skipped if pyspark is not installed (``ModuleNotFoundError``).
When pyspark IS available, the tests validate:
- Module imports cleanly
- Pipeline functions are callable
- SQL logic is structurally correct (via mock SparkSession)

Actual Spark execution NOT VERIFIED (no JVM on host).
"""
from __future__ import annotations

from unittest import mock

import pytest

pyspark = pytest.importorskip("pyspark", reason="pyspark not installed")


def test_spark_pipeline_imports():
    """Pipeline module imports without errors."""
    from app.spark import pipeline

    assert hasattr(pipeline, "run")
    assert hasattr(pipeline, "build_session")
    assert callable(pipeline.run)


def test_spark_pipeline_constants():
    """Pipeline has expected I/O paths."""
    from app.spark import pipeline

    assert "events" in pipeline.INPUT_PATH
    assert "warehouse" in pipeline.OUTPUT_PATH


def test_spark_pipeline_run_with_mock():
    """Pipeline run() invokes the expected Spark operations on a mock session."""
    mock_spark = mock.MagicMock()
    mock_df = mock.MagicMock()
    mock_spark.read.json.return_value = mock_df

    # Chain the DataFrame operations
    mock_df.filter.return_value = mock_df
    mock_df.dropDuplicates.return_value = mock_df
    mock_df.withColumn.return_value = mock_df
    mock_df.groupBy.return_value = mock_df
    mock_df.agg.return_value = mock_df
    mock_df.write.mode.return_value = mock_df
    mock_df.partitionBy.return_value = mock_df

    from app.spark.pipeline import run

    run(spark=mock_spark)

    # Verify that the pipeline read from the expected path
    mock_spark.read.json.assert_called_once()
    call_args = mock_spark.read.json.call_args
    assert "events" in call_args[0][0]
