"""The DuckDB warehouse: a single file that we query with SQL.

Look inside it from the terminal:
    python -m listings.warehouse "SELECT * FROM staging.valid LIMIT 5"
"""

import sys
import time

import duckdb

from listings.config import DATA_DIR, PROJECT_ROOT

WAREHOUSE = DATA_DIR / "warehouse.duckdb"
SQL_DIR = PROJECT_ROOT / "sql"


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    WAREHOUSE.parent.mkdir(parents=True, exist_ok=True)
    # DuckDB lets one process use the file at a time. If a task of another DAG has it open, wait for it.
    for _ in range(30):
        try:
            return duckdb.connect(str(WAREHOUSE), read_only=read_only)
        except duckdb.IOException:
            time.sleep(1)
    return duckdb.connect(str(WAREHOUSE), read_only=read_only)


def read_sql(name: str) -> str:
    return (SQL_DIR / f"{name}.sql").read_text()


def replace_partition(conn: duckdb.DuckDBPyConnection, table: str, select_sql: str, params: dict) -> None:
    """Make `table` hold exactly the rows of `select_sql` for this run_date.

    Delete the day, then insert the day, inside one transaction. Running it twice
    gives the same table, and a failure halfway leaves the old rows in place.
    """
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {table.split('.')[0]}")
    conn.execute(f"CREATE TABLE IF NOT EXISTS {table} AS SELECT * FROM ({select_sql}) LIMIT 0", params)
    conn.begin()
    conn.execute(f"DELETE FROM {table} WHERE run_date = $run_date::DATE", {"run_date": params["run_date"]})
    conn.execute(f"INSERT INTO {table} BY NAME {select_sql}", params)
    conn.commit()


if __name__ == "__main__":
    conn = connect(read_only=True)
    conn.sql(sys.argv[1]).show(max_width=200, max_rows=50)
    conn.close()
