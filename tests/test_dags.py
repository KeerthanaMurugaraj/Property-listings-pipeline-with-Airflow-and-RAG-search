"""Do the DAG files load, and do the production DAGs have the shape we expect?"""

import pytest
from airflow.models import DagBag


@pytest.fixture(scope="module")
def dagbag():
    return DagBag()


def test_all_dags_import_without_errors(dagbag):
    assert dagbag.import_errors == {}


def test_daily_dag_ends_with_build_listings(dagbag):
    dag = dagbag.dags["listings_daily"]
    assert [task.task_id for task in dag.leaves] == ["build_listings"]
    assert dag.max_active_runs == 1


def test_every_production_task_retries(dagbag):
    for dag_id in ["listings_daily", "listings_index"]:
        for task in dagbag.dags[dag_id].tasks:
            assert task.retries >= 1, f"{dag_id}.{task.task_id} has no retries"
