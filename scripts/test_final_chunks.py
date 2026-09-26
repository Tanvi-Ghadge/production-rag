from pprint import pprint

from rag.chunking import chunk_document
from rag.metadata import enrich_chunks
from rag.structure import normalize_document


PDF_PATH = "data/raw/Q3_2026_business_review.pdf"


def main():
    document = normalize_document(PDF_PATH)

    chunks = chunk_document(document)

    result = enrich_chunks(
        chunks,
        batch_size=5,
        max_retries=3,
    )

    if result.failures:
        print("Metadata generation failures:")

        for failure in result.failures:
            pprint(failure)

        return

    print(
        f"\nFinal enriched chunks: "
        f"{len(result.chunks)}"
    )

    for index, chunk in enumerate(result.chunks):

        print("\n" + "=" * 80)

        print(
            f"CHUNK {index + 1}"
        )

        print(
            f"ID: "
            f"{chunk['metadata']['chunk_id']}"
        )

        print("\nTEXT:")
        print(chunk["text"])

        print("\nMETADATA:")
        pprint(chunk["metadata"])

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()