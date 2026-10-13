"""Run the SQL files against a few hand-written rows in an empty in-memory database."""

import duckdb
import pytest

from listings import warehouse

PARAMS = {"run_date": "2026-10-01"}
COLUMNS = (
    "run_date, source, source_id, title, description, property_type, "
    "commune, address, price_eur, area_m2, bedrooms, features"
)


def _row(source, source_id, address="1 rue du fort", price=1500, property_type="apartment"):
    return (
        f"(DATE '2026-10-01', '{source}', '{source_id}', 'title', 'description', '{property_type}', "
        f"'Mersch', '{address}', {price}, 60, 2, ['lift'])"
    )


@pytest.fixture
def conn():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE SCHEMA staging")
    yield conn
    conn.close()


def test_validate_rejects_a_missing_price(conn):
    rows = ", ".join([_row("agency_a", "A-1"), _row("agency_a", "A-2", price="NULL")])
    conn.execute(f"CREATE TABLE staging.normalized AS SELECT * FROM (VALUES {rows}) t({COLUMNS})")

    result = conn.execute(
        f"SELECT source_id, reject_reason FROM ({warehouse.read_sql('validate')}) ORDER BY source_id", PARAMS
    ).fetchall()

    assert result == [("A-1", None), ("A-2", "price missing or not a number")]


def test_dedupe_merges_the_same_address_from_two_agencies(conn):
    rows = ", ".join(
        [
            _row("agency_a", "A-1", price=1500),
            _row("agency_b", "b1", price=1450),
            _row("agency_a", "A-2", address="2 rue du fort"),
        ]
    )
    conn.execute(f"CREATE TABLE staging.valid AS SELECT * FROM (VALUES {rows}) t({COLUMNS})")

    result = conn.execute(
        f"SELECT address, price_eur, sources FROM ({warehouse.read_sql('dedupe')}) ORDER BY address", PARAMS
    ).fetchall()

    assert result == [
        ("1 rue du fort", 1450, ["agency_a", "agency_b"]),
        ("2 rue du fort", 1500, ["agency_a"]),
    ]
