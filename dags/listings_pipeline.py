"""The property listings pipeline, as two DAGs:

    listings_daily   every day at 06:00:   extract -> load -> normalize -> validate -> deduplicate -> build_listings
    listings_index   whenever core.listings was rebuilt:   index_listings -> evaluate_index -> publish_index

The warehouse does not need to know that a search index exists. It only announces
"core.listings was updated" (an asset), and the index DAG listens for that.
"""

from datetime import timedelta

import pendulum
from airflow.sdk import Asset, dag, task
from airflow.sdk.exceptions import AirflowFailException

from listings.alerts import notify_failure

MAX_QUARANTINED_SHARE = 0.2
MIN_HIT_RATE = 0.8

core_listings = Asset("core_listings")

DEFAULT_ARGS = {
    "retries": 2,
    "retry_delay": timedelta(seconds=10),
    # Called once a task has failed for good, after its retries.
    "on_failure_callback": notify_failure,
}


@dag(
    schedule="0 6 * * *",  # every day at 06:00 UTC
    start_date=pendulum.datetime(2026, 10, 1, tz="UTC"),
    # Do not run all the missed days when the DAG is switched on. Old days are loaded with a backfill.
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["production"],
)
def listings_daily():
    @task
    def get_run_date(dag_run=None) -> str:
        return (dag_run.logical_date or dag_run.run_after).strftime("%Y-%m-%d")

    @task
    def simulate_agencies(run_date: str) -> str:
        from datetime import date

        from sources import generate

        generate.write_files(date.fromisoformat(run_date))
        return run_date

    @task
    def extract_agency_a(run_date: str) -> dict:
        from listings import extract

        return extract.extract_agency_a(run_date)

    @task
    def extract_agency_b(run_date: str) -> dict:
        from airflow.sdk import Connection

        from listings import extract

        # The address (and in real life the password) lives in Airflow, not in the code.
        conn = Connection.get("agency_b")
        return extract.extract_agency_b(run_date, base_url=f"http://{conn.host}:{conn.port}")

    @task
    def extract_agency_c(run_date: str) -> dict:
        from listings import extract

        return extract.extract_agency_c(run_date)

    @task
    def load_raw(run_date: str, extracted: list[dict]) -> str:
        from listings import load

        counts = load.load_raw(run_date, {e["source"]: e["path"] for e in extracted})
        print(f"rows loaded into raw tables: {counts}")
        return run_date

    @task
    def normalize(run_date: str) -> str:
        from listings import transform

        print(f"rows in staging.normalized for {run_date}: {transform.normalize(run_date)}")
        return run_date

    @task
    def validate(run_date: str) -> str:
        from listings import transform

        result = transform.validate(run_date)
        print(f"valid={result['valid']} quarantined={result['quarantined']}")
        for reason in result["reasons"]:
            print(f"  {reason}")
        share = result["quarantined"] / max(result["valid"] + result["quarantined"], 1)
        if share > MAX_QUARANTINED_SHARE:
            raise AirflowFailException(f"{share:.0%} of rows were quarantined, limit is {MAX_QUARANTINED_SHARE:.0%}")
        return run_date

    @task
    def deduplicate(run_date: str) -> str:
        from listings import transform

        print(f"{run_date}: {transform.deduplicate(run_date)}")
        return run_date

    # outlets: when this task succeeds, Airflow records that the asset was updated.
    @task(outlets=[core_listings])
    def build_listings(run_date: str) -> dict:
        from listings import transform

        counts = transform.build_listings()
        print(f"core.listings after processing {run_date}: {counts}")
        return counts

    run_date = simulate_agencies(get_run_date())
    extracted = [extract_agency_a(run_date), extract_agency_b(run_date), extract_agency_c(run_date)]
    build_listings(deduplicate(validate(normalize(load_raw(run_date, extracted)))))


@dag(
    schedule=[core_listings],  # no clock: runs when the asset was updated
    start_date=pendulum.datetime(2026, 10, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["production"],
)
def listings_index():
    @task
    def index_listings() -> dict:
        from listings import index

        result = index.sync()
        print(f"index: {result}")
        return result

    @task
    def evaluate_index(indexed: dict) -> dict:
        from rag import evaluate

        result = evaluate.hit_rate(indexed["index_version"])
        print(f"index version {indexed['index_version']}: {result}")
        if result["hit_rate"] < MIN_HIT_RATE:
            raise AirflowFailException(f"hit rate {result['hit_rate']:.0%} is below {MIN_HIT_RATE:.0%}, not publishing")
        return {"version": indexed["index_version"], "hit_rate": result["hit_rate"], "listings": result["listings"]}

    @task
    def publish_index(evaluated: dict) -> dict:
        from rag import store

        pointer = store.publish(evaluated["version"], evaluated)
        print(f"published: {pointer}")
        return pointer

    publish_index(evaluate_index(index_listings()))


listings_daily()
listings_index()
