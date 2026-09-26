from pprint import pprint

from rag.metadata import enrich_chunk
from rag.structure import normalize_document
from rag.chunking import chunk_document


PDF_PATH = "data/raw/Q3_2026_business_review.pdf"


def main():
    # 1. Parse + normalize the document
    document = normalize_document(PDF_PATH)

    # 2. Chunk the document
    chunks = chunk_document(document)

    print(f"Total chunks: {len(chunks)}")

    if not chunks:
        raise ValueError("No chunks were generated.")

    # 3. Take only the first real chunk
    chunk = chunks[0]

    print("\n--- Original Chunk ---")
    pprint(chunk)

    # 4. Generate metadata for this chunk
    enriched_chunk = enrich_chunk(chunk)

    print("\n--- Enriched Chunk ---")
    pprint(enriched_chunk)


if __name__ == "__main__":
    main()