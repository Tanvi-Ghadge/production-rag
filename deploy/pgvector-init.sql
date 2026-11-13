CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    parent_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    tenant TEXT NOT NULL,
    section_path TEXT NOT NULL,
    text TEXT NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    kind TEXT NOT NULL,
    effective_date DATE,
    embedding vector(384) NOT NULL,
    embedding_model TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS chunks_tenant_date_idx ON chunks (tenant, effective_date);
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);
