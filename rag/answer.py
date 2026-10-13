from rag import config, embeddings, store

SYSTEM = (
    "You help people find a home to rent in Luxembourg, using only the listings in the user message. "
    "Recommend the listings that fit the question and say why, giving the listing id in brackets, like [0eb372d053bb]. "
    "If no listing fits, say so instead of guessing."
)


def retrieve(question: str, k: int = config.TOP_K) -> list[dict]:
    """Search the published index version, never the latest one."""
    pointer = store.published()
    if pointer is None:
        raise RuntimeError("No index has been published yet. Run the listings_daily and listings_index DAGs first.")
    [vector] = embeddings.embed_queries([question])
    return store.search(vector, k, pointer["version"])


def answer(question: str, hits: list[dict]) -> str:
    import anthropic

    listings = "\n\n".join(f'<listing id="{hit["listing_id"]}">\n{hit["text"]}\n</listing>' for hit in hits)
    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=config.ANSWER_MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"{listings}\n\nQuestion: {question}"}],
        # If a safety classifier declines the request, the API retries it on a fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        return "The model declined to answer this question."
    return "".join(block.text for block in response.content if block.type == "text")
