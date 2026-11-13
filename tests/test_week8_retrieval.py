from datetime import date
from pathlib import Path

from ingest.embedder import HashEmbedder
from retrieval.bm25 import BM25Index
from retrieval.dense import VectorIndex
from retrieval.hybrid import HybridRetriever
from retrieval.interface import RetrievalFilters
from retrieval.rerank import CrossEncoderReranker


def _documents(tmp_path: Path) -> list[dict[str, object]]:
    embedder = HashEmbedder(tmp_path / "cache.json")
    texts = [
        ("a", "A", "UPI payment aggregator settlement", "2020-01-01"),
        ("b", "B", "UPI payment aggregator KYC", "2025-01-01"),
        ("c", "A", "unrelated foreign exchange rule", "2026-01-01"),
    ]
    return [
        {
            "chunk_id": chunk_id,
            "tenant": tenant,
            "text": text,
            "effective_date": effective,
            "embedding": embedder.embed([text])[0],
        }
        for chunk_id, tenant, text, effective in texts
    ]


def test_bm25_and_dense_apply_tenant_and_date_filters(tmp_path: Path) -> None:
    documents = _documents(tmp_path)
    filters = RetrievalFilters(tenant="A", effective_after=date(2021, 1, 1))
    bm25 = BM25Index(documents)
    dense = VectorIndex(documents)
    assert [doc["chunk_id"] for doc, _ in bm25.search("UPI", filters=filters)] == []
    query_vector = documents[1]["embedding"]
    assert [doc["chunk_id"] for doc, _ in dense.search(query_vector, filters=filters)] == ["c"]


def test_hybrid_fuses_results_without_duplicates(tmp_path: Path) -> None:
    documents = _documents(tmp_path)
    embedder = HashEmbedder(tmp_path / "query-cache.json")
    results = HybridRetriever(BM25Index(documents), VectorIndex(documents), embedder).retrieve("UPI")
    ids = [doc["chunk_id"] for doc, _ in results]
    assert len(ids) == len(set(ids))
    assert ids[0] in {"a", "b"}


def test_cross_encoder_reranker_uses_scorer_and_top_k(tmp_path: Path) -> None:
    documents = _documents(tmp_path)
    candidates = [(documents[0], 0.1), (documents[1], 0.2)]
    reranker = CrossEncoderReranker(scorer=lambda pairs: [0.2, 0.9])
    results = reranker.rerank("KYC", candidates, top_k=1)
    assert results[0][0]["chunk_id"] == "b"
