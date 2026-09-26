import argparse

from rag.chunking import chunk_document
from rag.structure import normalize_document


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest and chunk a document."
    )

    parser.add_argument(
        "path",
        help="Path to the document",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=512,
        help="Target chunk size in tokens",
    )

    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=64,
        help="Chunk overlap in tokens",
    )

    args = parser.parse_args()

    document = normalize_document(args.path)

    print("=" * 80)
    print("DOCUMENT")
    print("=" * 80)

    print(f"Title:      {document.title}")
    print(f"Source:     {document.source}")
    print(f"File type:  {document.file_type}")
    print(f"Characters: {len(document.text)}")

    chunks = chunk_document(
        document,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    print()
    print("=" * 80)
    print(f"CHUNKS: {len(chunks)}")
    print("=" * 80)

    for index, chunk in enumerate(chunks[:10]):
        print()
        print(f"--- CHUNK {index + 1} ---")
        print(f"Metadata: {chunk['metadata']}")
        print(chunk["text"][:1000])


if __name__ == "__main__":
    main()