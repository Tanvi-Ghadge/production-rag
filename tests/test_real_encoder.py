from pathlib import Path

from ingest.embedder import SentenceTransformerEmbedder


def test_real_encoder_is_model_aware_and_normalized(tmp_path: Path) -> None:
    embedder = SentenceTransformerEmbedder(tmp_path / "cache.json")
    vectors = embedder.embed(["payment aggregator rules"])
    assert embedder.model_name == "BAAI/bge-small-en-v1.5"
    assert embedder.dimensions == 384
    assert len(vectors[0]) == 384
    assert abs(sum(value * value for value in vectors[0]) ** 0.5 - 1.0) < 1e-4
    embedder.embed(["payment aggregator rules"])
    assert embedder.cache_hits == 1
    assert embedder.cache_misses == 1
