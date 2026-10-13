"""Index: keep the vector index in step with core.listings, embedding only what changed.

Try a search from the terminal:
    python -m listings.index "furnished studio with parking"
"""

import sys

from listings import warehouse
from rag import config, embeddings, store


def sync() -> dict:
    """Compare the warehouse with the index and apply only the difference."""
    conn = warehouse.connect(read_only=True)
    wanted = conn.execute(warehouse.read_sql("listing_documents")).fetch_arrow_table().to_pylist()
    conn.close()

    indexed = store.indexed_fingerprints()
    wanted_ids = {row["listing_id"] for row in wanted}
    # New listings are not in the index yet; changed ones are there with another fingerprint.
    to_embed = [row for row in wanted if indexed.get(row["listing_id"]) != row["fingerprint"]]
    to_delete = sorted(set(indexed) - wanted_ids)

    if to_embed:
        vectors = embeddings.embed_passages([row["text"] for row in to_embed])
        for row, vector in zip(to_embed, vectors):
            row["vector"] = vector
    version = store.apply_changes(to_embed, to_delete) if to_embed or to_delete else store.latest_version()

    return {
        "embedded": len(to_embed),
        "deleted": len(to_delete),
        "unchanged": len(wanted) - len(to_embed),
        "index_version": version,
    }


if __name__ == "__main__":
    [vector] = embeddings.embed_queries([sys.argv[1]])
    for hit in store.search(vector, config.TOP_K):
        print(f"{hit['_distance']:.3f}  {hit['listing_id']}  {hit['text']}")
