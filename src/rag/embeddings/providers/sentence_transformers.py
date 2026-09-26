from functools import lru_cache

from sentence_transformers import SentenceTransformer, SparseEncoder

from rag.embeddings.models import (
    DenseEmbedding,
    SparseEmbedding,
)


DENSE_MODEL_NAME = "BAAI/bge-base-en-v1.5"
SPARSE_MODEL_NAME = "naver/splade-cocondenser-ensembledistil"


@lru_cache(maxsize=1)
def _get_dense_model() -> SentenceTransformer:
    return SentenceTransformer(DENSE_MODEL_NAME)


@lru_cache(maxsize=1)
def _get_sparse_model() -> SparseEncoder:
    return SparseEncoder(SPARSE_MODEL_NAME)


def generate_dense_embeddings(
    texts: list[str],
) -> list[DenseEmbedding]:
    if not texts:
        return []

    model = _get_dense_model()

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    return [
        DenseEmbedding(
            values=embedding.tolist()
        )
        for embedding in embeddings
    ]


def generate_sparse_embeddings(
    texts: list[str],
) -> list[SparseEmbedding]:
    if not texts:
        return []

    model = _get_sparse_model()

    embeddings = model.encode(
        texts,
        convert_to_sparse_tensor=True,
        show_progress_bar=True,
    )

    embeddings = embeddings.coalesce()

    results: list[SparseEmbedding] = []

    for row in range(embeddings.shape[0]):
        row_tensor = embeddings[row].coalesce()

        raw_indices = row_tensor.indices()

        indices = raw_indices[-1].tolist()
        values = row_tensor.values().tolist()

        results.append(
            SparseEmbedding(
                indices=indices,
                values=values,
            )
        )

    return results