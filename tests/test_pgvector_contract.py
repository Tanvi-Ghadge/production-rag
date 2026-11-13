from pathlib import Path

from ingest.pgvector_indexer import PgVectorIndex, _params
from retrieval.pgvector import PgVectorRetriever


def test_pgvector_schema_and_vector_parameter_contract() -> None:
    schema = Path("deploy/pgvector-init.sql").read_text(encoding="utf-8")
    assert "vector(384)" in schema
    assert "hnsw" in schema
    assert "tenant, effective_date" in schema
    assert _params({
        "chunk_id": "c", "parent_id": "p", "document_id": "d", "tenant": "A",
        "section_path": "s", "text": "t", "page_start": 1, "page_end": 1,
        "content_hash": "h", "kind": "child", "effective_date": None,
        "embedding": [0.0, 1.0], "embedding_model": "test",
    })[-2] == "[0.0,1.0]"
    assert PgVectorRetriever._vector_literal([0.0, 1.0]) == "[0.0,1.0]"
