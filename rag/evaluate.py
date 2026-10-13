import json

from rag import config, embeddings, store


def _matches(row: dict, expect: dict) -> bool:
    return all(row[column] == value for column, value in expect.items())


def hit_rate(version: int, k: int = config.TOP_K) -> dict:
    """Share of golden questions with at least one fitting listing in the top ``k`` results.

    A golden question names what a good result looks like (for example a studio in
    Esch-sur-Alzette), not one listing, because listings come and go every day.
    """
    cases = [json.loads(line) for line in config.EVAL_FILE.read_text().splitlines() if line.strip()]
    listings = store.listings(version)
    # A question nobody could answer today (no such listing on the market) is not counted.
    cases = [case for case in cases if any(_matches(row, case["expect"]) for row in listings)]
    vectors = embeddings.embed_queries([case["question"] for case in cases])

    misses = []
    for case, vector in zip(cases, vectors):
        hits = store.search(vector, k, version)
        if not any(_matches(hit, case["expect"]) for hit in hits):
            misses.append(case["question"])

    return {
        "hit_rate": (len(cases) - len(misses)) / len(cases) if cases else 0.0,
        "questions": len(cases),
        "listings": len(listings),
        "misses": misses,
    }
