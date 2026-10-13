from functools import lru_cache

from rag import config


@lru_cache(maxsize=1)
def _model():
    # Imported here, not at module top: the model is heavy, and Airflow re-parses
    # DAG files constantly. Anything a DAG imports must stay cheap to import.
    from fastembed import TextEmbedding

    return TextEmbedding(config.EMBEDDING_MODEL)


def embed_passages(texts: list[str]) -> list[list[float]]:
    return [vector.tolist() for vector in _model().embed(texts)]


def embed_queries(texts: list[str]) -> list[list[float]]:
    return [vector.tolist() for vector in _model().query_embed(texts)]
