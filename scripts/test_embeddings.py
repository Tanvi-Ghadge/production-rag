from rag.embeddings import generate_chunk_embeddings


chunks = [
    {
        "text": (
            "Infrastructure costs increased from ₹3.8 Cr "
            "in Q1 to ₹5.6 Cr in Q3."
        ),
        "metadata": {
            "chunk_id": "test-0001",
        },
    },
    {
        "text": (
            "North America revenue increased by 17.9% "
            "during the quarter."
        ),
        "metadata": {
            "chunk_id": "test-0002",
        },
    },
]


embedded_chunks = generate_chunk_embeddings(chunks)


for chunk in embedded_chunks:
    embedding = chunk["embedding"]

    print(
        f"\nChunk: {chunk['metadata']['chunk_id']}"
    )

    print(
        f"Dense dimensions: "
        f"{len(embedding.dense.values)}"
    )

    print(
        f"Sparse non-zero values: "
        f"{len(embedding.sparse.indices)}"
    )