from datetime import date
from pathlib import Path

from ingest.embedder import SentenceTransformerEmbedder
from ingest.indexer import LocalIndex
from retrieval.interface import RetrievalFilters


def test_frozen_index_supports_filtered_hybrid_retrieval(tmp_path: Path) -> None:
    index = LocalIndex(Path("data/index"))
    chunks = index.load_chunks()
    assert len(chunks) in (5029, 5256)
    assert all("effective_date" in chunk for chunk in chunks)
    embedder = SentenceTransformerEmbedder(tmp_path / "query-cache.json")
    results = index.hybrid(embedder).retrieve(
        "KYC requirements",
        top_k=10,
        filters=RetrievalFilters(tenant="B", effective_after=date(2024, 1, 1)),
    )
    assert results
    assert all(document["tenant"] == "B" for document, _ in results)
    assert all(date.fromisoformat(str(document["effective_date"])) >= date(2024, 1, 1)
               for document, _ in results)
