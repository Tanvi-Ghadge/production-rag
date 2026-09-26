from rag.structure import normalize_document
from rag.chunking import chunk_document
from rag.metadata.generator import enrich_chunks
from rag.embeddings import generate_chunk_embeddings
from rag.vectorstore import upsert_chunks


FILE_PATH = "data/raw/Q3_2026_business_review.pdf"


def main():
    # 1. Parse + normalize
    document = normalize_document(FILE_PATH)

    print(f"Loaded document: {document.title}")

    # 2. Chunk
    chunks = chunk_document(document)

    print(f"Created {len(chunks)} chunks")

    # 3. Generate metadata
    metadata_result = enrich_chunks(
        chunks,
        batch_size=5,
        max_retries=3,
    )

    if metadata_result.failures:
        print(
            f"Metadata generation failed for "
            f"{len(metadata_result.failures)} batches."
        )

        for failure in metadata_result.failures:
            print(failure)

        raise RuntimeError(
            "Stopping indexing because metadata generation failed."
        )

    enriched_chunks = metadata_result.chunks

    print(
        f"Generated metadata for "
        f"{len(enriched_chunks)} chunks"
    )

    # 4. Generate dense + sparse embeddings
    embedded_chunks = generate_chunk_embeddings(
        enriched_chunks
    )

    print(
        f"Generated embeddings for "
        f"{len(embedded_chunks)} chunks"
    )

    # 5. Store vectors + metadata in Pinecone
    upsert_chunks(embedded_chunks)

    print("Indexing completed successfully.")


if __name__ == "__main__":
    main()