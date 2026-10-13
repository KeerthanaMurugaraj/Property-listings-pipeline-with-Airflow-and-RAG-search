"""The vector index: one LanceDB table with one row per active listing.

LanceDB keeps every write as a new table version. Readers
only open the version named in ``published.json``, and the pointer moves only
after the new version passes a quality check.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import lancedb
import pyarrow as pa

from rag import config

TABLE = "listings"

SCHEMA = pa.schema(
    [
        pa.field("listing_id", pa.string()),
        pa.field("fingerprint", pa.string()),
        pa.field("text", pa.string()),
        pa.field("commune", pa.string()),
        pa.field("property_type", pa.string()),
        pa.field("price_eur", pa.int32()),
        pa.field("bedrooms", pa.int32()),
        pa.field("vector", pa.list_(pa.float32(), config.EMBEDDING_DIM)),
    ]
)


def _db():
    return lancedb.connect(config.INDEX_DIR / "lancedb")


def _pointer_path() -> Path:
    return config.INDEX_DIR / "published.json"


def open_table(version: int | None = None):
    """Return the listings table (latest, or pinned to ``version``), or None if it does not exist yet."""
    db = _db()
    if TABLE not in db.table_names():
        return None
    table = db.open_table(TABLE)
    if version is not None:
        table.checkout(version)
    return table


def indexed_fingerprints() -> dict[str, str]:
    """Map listing_id -> fingerprint for everything currently in the index."""
    table = open_table()
    if table is None:
        return {}
    rows = table.search().select(["listing_id", "fingerprint"]).to_arrow().to_pylist()
    return {row["listing_id"]: row["fingerprint"] for row in rows}


def apply_changes(rows: list[dict], deleted_ids: list[str]) -> int | None:
    """Write new and changed listings, drop deleted ones, return the new table version.

    Safe to run twice with the same input: the old row of a listing is deleted
    before its new row is added, so a retry never produces duplicates.
    """
    new = pa.Table.from_pylist(rows, schema=SCHEMA) if rows else None
    stale = set(deleted_ids) | {row["listing_id"] for row in rows}

    table = open_table()
    if table is None:
        return _db().create_table(TABLE, data=new, schema=SCHEMA).version if new is not None else None

    if stale:
        quoted = ", ".join(f"'{listing_id}'" for listing_id in sorted(stale))
        table.delete(f"listing_id IN ({quoted})")
    if new is not None:
        table.add(new)
    return table.version


METADATA = ["listing_id", "text", "commune", "property_type", "price_eur", "bedrooms"]


def latest_version() -> int | None:
    table = open_table()
    return table.version if table is not None else None


def listings(version: int | None = None) -> list[dict]:
    """Every listing in the index, without the vectors."""
    table = open_table(version)
    return table.search().select(METADATA).to_arrow().to_pylist() if table is not None else []


def search(vector: list[float], k: int, version: int | None = None) -> list[dict]:
    table = open_table(version)
    if table is None:
        return []
    return table.search(vector).distance_type("cosine").limit(k).select([*METADATA, "_distance"]).to_list()


def publish(version: int, metrics: dict) -> dict:
    pointer = {
        "version": version,
        "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **metrics,
    }
    path = _pointer_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(pointer, indent=2))
    # os.replace is atomic: a reader sees the old pointer or the new one, never half a file.
    os.replace(tmp, path)
    return pointer


def published() -> dict | None:
    path = _pointer_path()
    return json.loads(path.read_text()) if path.exists() else None
