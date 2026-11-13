from pathlib import Path

from ingest.chunker import structure_aware_chunks
from ingest.embedder import HashEmbedder
from ingest.indexer import LocalIndex
from ingest.parsers.pdf import ParsedDocument, ParsedPage
from retrieval.bm25 import BM25Index
from retrieval.dense import VectorIndex


def _document() -> ParsedDocument:
    return ParsedDocument(
        "example.pdf",
        (ParsedPage(1, "1. Payment rules\nUPI payment aggregator obligations and settlement requirements."),),
        "1. Payment rules\nUPI payment aggregator obligations and settlement requirements.",
    )


def test_structure_aware_chunks_have_parent_relationships() -> None:
    chunks = structure_aware_chunks(_document(), "A:example", "A", child_words=5, overlap_words=1)
    parents = {chunk.chunk_id for chunk in chunks if chunk.kind == "parent"}
    children = [chunk for chunk in chunks if chunk.kind == "child"]
    assert parents
    assert children
    assert all(child.parent_id in parents for child in children)


def test_hash_embedder_is_cached_by_content(tmp_path: Path) -> None:
    embedder = HashEmbedder(tmp_path / "cache.json")
    first = embedder.embed(["same text"])
    second = embedder.embed(["same text"])
    assert first == second
    assert embedder.cache_misses == 1
    assert embedder.cache_hits == 1


def test_indexes_search_persisted_chunks(tmp_path: Path) -> None:
    index = LocalIndex(tmp_path)
    embedder = HashEmbedder(tmp_path / "cache.json")
    chunks = structure_aware_chunks(_document(), "A:example", "A")
    changed, total = index.upsert(chunks, embedder)
    assert changed == len(chunks)
    assert total == len(chunks)
    assert BM25Index(index.load_chunks()).search("UPI obligations")
    query_vector = embedder.embed(["UPI obligations"])[0]
    assert VectorIndex(index.load_chunks()).search(query_vector)


def test_repeated_upsert_creates_no_duplicates_or_embeddings(tmp_path: Path) -> None:
    index = LocalIndex(tmp_path)
    embedder = HashEmbedder(tmp_path / "cache.json")
    chunks = structure_aware_chunks(_document(), "A:example", "A")
    index.upsert(chunks, embedder)
    changed, total = index.upsert(chunks, embedder)
    assert changed == 0
    assert total == len(chunks)
    assert len(index.load_chunks()) == len(chunks)
