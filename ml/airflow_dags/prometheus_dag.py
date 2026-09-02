"""Airflow DAG: MLOps lifecycle for the Prometheus router model.

drift check → (re)train → evaluate → promotion gate → register.
Scheduler execution NOT VERIFIED on Windows; DAG structure is import-checked.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "prometheus",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def _check_drift(**_):
    from app.ml.drift import detect_drift
    from app.ml.dataset import FEATURE_NAMES, build_dataset, extract_features

    base = build_dataset(seed=42)
    reference = {f: [row[f] for row in base.features] for f in FEATURE_NAMES}
    current_rows = [extract_features(t) for t in base.texts[-20:]]
    current = {f: [row[f] for row in current_rows] for f in FEATURE_NAMES}
    report = detect_drift(reference, current, threshold=0.2)
    return report.to_dict()


def _train(**_):
    from app.ml.train import train_router_model

    return train_router_model(seed=45)


def _promote(**_):
    from app.ml.retrain import retrain

    return retrain(seed=46)


with DAG(
    dag_id="prometheus_mlops",
    schedule="0 9 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
) as dag:
    drift = PythonOperator(task_id="check_drift", python_callable=_check_drift)
    train = PythonOperator(task_id="train_candidate", python_callable=_train)
    promote = PythonOperator(task_id="evaluate_and_promote", python_callable=_promote)

    drift >> train >> promote
