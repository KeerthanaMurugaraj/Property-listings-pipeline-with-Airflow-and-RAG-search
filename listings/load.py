"""Load: put each day's raw file into a raw table, still without cleaning anything.

After this step everything is reachable with SQL, which is where the cleaning happens.
"""

from xml.etree import ElementTree as ET

import pyarrow as pa

from listings import warehouse

# DuckDB reads CSV and JSON files by itself.
LOAD_CSV = "SELECT $run_date::DATE AS run_date, * FROM read_csv($path, all_varchar = true)"
LOAD_JSON = """
    SELECT $run_date::DATE AS run_date, unnest(listing)
    FROM (SELECT unnest(listings) AS listing FROM read_json($path))
"""
LOAD_XML = "SELECT $run_date::DATE AS run_date, * FROM xml_rows"


def _xml_rows(path: str) -> pa.Table:
    """DuckDB has no XML reader, so turn each <annonce> into a row of plain text first."""
    rows = [
        {
            "id": node.get("id"),
            "titre": node.findtext("titre"),
            "type": node.findtext("type"),
            "ville": node.findtext("ville"),
            "adresse": node.findtext("adresse"),
            "loyer": node.findtext("loyer"),
            "devise": node.find("loyer").get("devise"),
            "surface": node.findtext("surface"),
            "unite": node.find("surface").get("unite"),
            "chambres": node.findtext("chambres"),
            "equipements": [e.text for e in node.iter("equipement")],
            "description": node.findtext("description"),
            "langue": node.find("description").get("lang"),
        }
        for node in ET.parse(path).getroot().findall("annonce")
    ]
    return pa.Table.from_pylist(rows)


def load_raw(run_date: str, paths: dict[str, str]) -> dict[str, int]:
    """`paths` maps a source name to its raw file. Returns the row count per raw table for this day."""
    conn = warehouse.connect()
    conn.register("xml_rows", _xml_rows(paths["agency_c"]))
    warehouse.replace_partition(conn, "raw.agency_a", LOAD_CSV, {"run_date": run_date, "path": paths["agency_a"]})
    warehouse.replace_partition(conn, "raw.agency_b", LOAD_JSON, {"run_date": run_date, "path": paths["agency_b"]})
    warehouse.replace_partition(conn, "raw.agency_c", LOAD_XML, {"run_date": run_date})
    counts = {
        source: conn.execute(f"SELECT count(*) FROM raw.{source} WHERE run_date = ?::DATE", [run_date]).fetchone()[0]
        for source in paths
    }
    conn.close()
    return counts
