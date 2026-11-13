from __future__ import annotations

import argparse
from pathlib import Path

from ingest.embedder import SentenceTransformerEmbedder
from ingest.indexer import LocalIndex
from ingest.pgvector_indexer import PgVectorIndex


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default="postgresql://rag:rag@localhost:55432/rag")
    parser.add_argument("--index", type=Path, default=Path("data/index"))
    parser.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    args = parser.parse_args()
    index = LocalIndex(args.index)
    records = index.load_chunks()
    expected = [record for record in records if record.get("embedding_model") == args.model]
    if len(expected) != len(records):
        raise RuntimeError("local index contains vectors from a different embedding model")
    print(f"upserted {PgVectorIndex(args.dsn).upsert(expected)} chunks")


if __name__ == "__main__":
    main()
