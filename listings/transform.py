"""Transform: run the SQL in sql/ that turns three raw tables into one clean one."""

from listings import warehouse

SOURCES = ["agency_a", "agency_b", "agency_c"]


def normalize(run_date: str) -> int:
    """Bring all three sources to the same columns in staging.normalized."""
    # BY NAME matches columns by their name, so the three queries cannot get mixed up by position.
    select = "\nUNION ALL BY NAME\n".join(f"({warehouse.read_sql(f'normalize_{source}')})" for source in SOURCES)
    conn = warehouse.connect()
    warehouse.replace_partition(conn, "staging.normalized", select, {"run_date": run_date})
    rows = conn.execute("SELECT count(*) FROM staging.normalized WHERE run_date = ?::DATE", [run_date]).fetchone()[0]
    conn.close()
    return rows


def validate(run_date: str) -> dict:
    """Check every normalized row. Good rows show up in staging.valid, bad ones in staging.quarantine."""
    conn = warehouse.connect()
    warehouse.replace_partition(conn, "staging.checked", warehouse.read_sql("validate"), {"run_date": run_date})
    conn.execute(
        "CREATE OR REPLACE VIEW staging.valid AS "
        "SELECT * EXCLUDE (reject_reason) FROM staging.checked WHERE reject_reason IS NULL"
    )
    conn.execute(
        "CREATE OR REPLACE VIEW staging.quarantine AS SELECT * FROM staging.checked WHERE reject_reason IS NOT NULL"
    )
    valid = conn.execute("SELECT count(*) FROM staging.valid WHERE run_date = ?::DATE", [run_date]).fetchone()[0]
    reasons = conn.execute(
        "SELECT source, reject_reason, count(*) FROM staging.quarantine "
        "WHERE run_date = ?::DATE GROUP BY ALL ORDER BY ALL",
        [run_date],
    ).fetchall()
    conn.close()
    return {
        "valid": valid,
        "quarantined": sum(count for _, _, count in reasons),
        "reasons": [f"{source}: {reason} ({count})" for source, reason, count in reasons],
    }


def deduplicate(run_date: str) -> dict:
    """Merge rows that describe the same property into staging.deduped."""
    conn = warehouse.connect()
    warehouse.replace_partition(conn, "staging.deduped", warehouse.read_sql("dedupe"), {"run_date": run_date})
    properties, merged = conn.execute(
        "SELECT count(*), count(*) FILTER (len(sources) > 1) FROM staging.deduped WHERE run_date = ?::DATE",
        [run_date],
    ).fetchone()
    conn.close()
    return {"properties": properties, "listed_by_two_agencies": merged}


def build_listings() -> dict:
    """Rebuild core.listings, the current state of every property ever seen."""
    conn = warehouse.connect()
    conn.execute("CREATE SCHEMA IF NOT EXISTS core")
    conn.execute(f"CREATE OR REPLACE TABLE core.listings AS {warehouse.read_sql('listings')}")
    counts = dict(conn.execute("SELECT status, count(*) FROM core.listings GROUP BY status").fetchall())
    conn.close()
    return counts
