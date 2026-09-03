"""Airflow DAG import test — validates DAG structure without a scheduler.

This test imports the DAG definition and checks:
- No import errors (catches broken module references)
- Expected task count (3: check_drift, train_candidate, evaluate_and_promote)
- Correct dependency chain (check_drift >> train_candidate >> evaluate_and_promote)

Scheduler execution NOT VERIFIED on Windows; this is import-only verification.
"""
from __future__ import annotations

import importlib
import sys
from unittest import mock


def _stub_airflow():
    """Create minimal stubs so the DAG file can be imported without airflow."""
    dag_instances: list = []

    class FakeDAG:
        def __init__(self, **kwargs):
            self.dag_id = kwargs.get("dag_id", "unknown")
            self.tasks: list = []
            self._kwargs = kwargs
            dag_instances.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

    class FakeOperator:
        def __init__(self, **kwargs):
            self.task_id = kwargs.get("task_id", "unknown")
            self._downstream: list[FakeOperator] = []
            # register on the most-recent DAG
            if dag_instances:
                dag_instances[-1].tasks.append(self)

        def __rshift__(self, other):
            self._downstream.append(other)
            return other

    # Patch airflow modules
    airflow_mod = mock.MagicMock()
    airflow_mod.DAG = FakeDAG
    airflow_operators = mock.MagicMock()
    airflow_operators.python.PythonOperator = FakeOperator

    return {
        "airflow": airflow_mod,
        "airflow.operators": airflow_operators,
        "airflow.operators.python": airflow_operators.python,
    }, dag_instances


def test_dag_imports_without_errors():
    """DAG file can be imported (no syntax errors or broken references)."""
    stubs, dag_instances = _stub_airflow()

    # Remove any cached import so our stubs take effect
    mod_name = "ml.airflow_dags.prometheus_dag"
    sys.modules.pop(mod_name, None)

    with mock.patch.dict(sys.modules, stubs):
        mod = importlib.import_module(mod_name)

    assert mod is not None
    assert len(dag_instances) == 1, "expected exactly 1 DAG definition"


def test_dag_has_expected_tasks():
    """DAG contains the 3 expected tasks in the correct order."""
    stubs, dag_instances = _stub_airflow()

    mod_name = "ml.airflow_dags.prometheus_dag"
    sys.modules.pop(mod_name, None)

    with mock.patch.dict(sys.modules, stubs):
        importlib.import_module(mod_name)

    dag = dag_instances[0]
    task_ids = [t.task_id for t in dag.tasks]
    assert task_ids == ["check_drift", "train_candidate", "evaluate_and_promote"]


def test_dag_dependency_chain():
    """Tasks are wired: check_drift >> train_candidate >> evaluate_and_promote."""
    stubs, dag_instances = _stub_airflow()

    mod_name = "ml.airflow_dags.prometheus_dag"
    sys.modules.pop(mod_name, None)

    with mock.patch.dict(sys.modules, stubs):
        importlib.import_module(mod_name)

    dag = dag_instances[0]
    drift, train, promote = dag.tasks

    assert train in drift._downstream, "check_drift should >> train_candidate"
    assert promote in train._downstream, "train_candidate should >> evaluate_and_promote"


def test_dag_schedule():
    """DAG schedule is daily at 09:00."""
    stubs, dag_instances = _stub_airflow()

    mod_name = "ml.airflow_dags.prometheus_dag"
    sys.modules.pop(mod_name, None)

    with mock.patch.dict(sys.modules, stubs):
        importlib.import_module(mod_name)

    dag = dag_instances[0]
    assert dag._kwargs["schedule"] == "0 9 * * *"
    assert dag._kwargs["catchup"] is False
