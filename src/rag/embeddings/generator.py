from rag.embeddings.models import HybridEmbedding
from rag.embeddings.providers.sentence_transformers import (
    generate_dense_embeddings,
    generate_sparse_embeddings,
)


def generate_chunk_embeddings(
    chunks: list[dict],
) -> list[dict]:
    if not chunks:
        return []

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    dense_embeddings = generate_dense_embeddings(texts)
    sparse_embeddings = generate_sparse_embeddings(texts)

    if len(dense_embeddings) != len(chunks):
        raise ValueError(
            "Dense embedding count does not match chunk count."
        )

    if len(sparse_embeddings) != len(chunks):
        raise ValueError(
            "Sparse embedding count does not match chunk count."
        )

    embedded_chunks = []

    for chunk, dense, sparse in zip(
        chunks,
        dense_embeddings,
        sparse_embeddings,
    ):
        hybrid_embedding = HybridEmbedding(
            dense=dense,
            sparse=sparse,
        )

        embedded_chunks.append(
            {
                **chunk,
                "embedding": hybrid_embedding,
            }
        )

    return embedded_chunks