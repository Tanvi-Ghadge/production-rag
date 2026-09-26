from pprint import pprint

from rag.chunking import chunk_document
from rag.metadata import enrich_chunks
from rag.structure import normalize_document


PDF_PATH = "data/raw/Q3_2026_business_review.pdf"


def main():
    document = normalize_document(PDF_PATH)

    chunks = chunk_document(document)

    print(f"Total chunks: {len(chunks)}")

    result = enrich_chunks(
        chunks,
        batch_size=5,
        max_retries=3,
    )

    print(
        f"\nSuccessfully enriched: "
        f"{len(result.chunks)}"
    )

    print(
        f"Failed chunks/batches: "
        f"{len(result.failures)}"
    )

    print("\n--- Enriched chunks ---")

    for chunk in result.chunks:
        print(
            f"\nChunk ID: "
            f"{chunk['metadata']['chunk_id']}"
        )

        print(
            f"Summary: "
            f"{chunk['metadata']['summary']}"
        )

        print(
            f"Keywords: "
            f"{chunk['metadata']['keywords']}"
        )

        print(
            f"Question: "
            f"{chunk['metadata']['hypothetical_question']}"
        )

    if result.failures:
        print("\n--- Failures ---")

        for failure in result.failures:
            pprint(failure)


if __name__ == "__main__":
    main()