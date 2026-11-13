# Week 7 ingestion architecture

The frozen release in [`corpus.md`](corpus.md) is ingested with:

```text
corpus/raw/<tenant>/*.pdf
        -> pypdf parser
        -> whitespace cleanup and page boundaries
        -> heading-aware parent sections
        -> overlapping child chunks
        -> SHA-256 content-hash embedding cache
        -> persistent chunks.jsonl
        -> BM25 and cosine-vector indexes
```

Run the pipeline with:

```text
make ingest
```

The command reads `corpus/audit.csv`, writes derived state under
`data/index/`, and never modifies the frozen source PDFs. A source with no
extractable text is recorded as `needs_ocr` and contributes no answerable
chunks.

## Idempotence

Chunk IDs are deterministic from the document, section, offset, and text.
Each chunk also stores its content hash. The indexer upserts by chunk ID and
embeds only new or changed hashes. Re-running ingestion therefore preserves
the same chunk count and produces zero embedding work when the source bytes
are unchanged.

The persisted state records document/job status, chunk counts, changed chunks,
and embedding cache hits/misses. `chunks.jsonl` contains both parent and child
records; child records point to their parent through `parent_id`.

## Golden retrieval set

The Week 7 labeled set is
[`evals/golden/golden.jsonl`](../evals/golden/golden.jsonl). It contains 108
records with resolved chunk IDs and passages:

- 30 factoid;
- 13 multi-hop;
- 15 table/structured-passage lookup;
- 15 version-sensitive, using the frozen supersession pairs;
- 20 unanswerable/refusal cases; and
- 15 adversarial cases covering document prompt injection, PII requests, and
  off-topic or unsupported requests.

Run `python evals/golden/validate_golden.py` to verify the count, schema,
category coverage, and that every cited chunk exists in the local index.
Adversarial injected text is a marked test overlay and is never treated as a
corpus passage.

The Week 8 evaluator is exposed as `make eval-retrieval` and writes the
reproducible report to [`evals/results/retrieval.md`](../evals/results/retrieval.md)
and machine-readable metrics to
[`evals/results/retrieval.json`](../evals/results/retrieval.json). It runs
BM25, dense, hybrid RRF, and hybrid-plus-reranker over 200/400/800-word
children with zero or 50-word overlap. Embedding caches are kept under
`data/eval-cache/` and are not evaluation results.

## Production-like vector backend

[`deploy/docker-compose.pgvector.yml`](../deploy/docker-compose.pgvector.yml)
starts PostgreSQL 16 with pgvector. The schema and HNSW cosine index are in
[`deploy/pgvector-init.sql`](../deploy/pgvector-init.sql). The
[`PgVectorIndex`](../ingest/pgvector_indexer.py) performs idempotent chunk
upserts, and [`PgVectorRetriever`](../retrieval/pgvector.py) applies the same
tenant/date filters as local retrieval. Start it with `make pgvector-up` after
Docker Desktop is running.

## Local implementation boundary

The current Week 7 embedder is a deterministic local hashing embedder. It is
retained only as an explicit `--hash-embeddings` baseline. The default
ingestion encoder is the configurable Hugging Face
`BAAI/bge-small-en-v1.5` sentence-transformers model (384 dimensions).
Embedding cache keys include both model name and content hash, and each
persisted chunk records `embedding_model`; changing models therefore
re-embeds safely instead of mixing vector spaces.

## Week 8 retrieval

All local retrievers use the `Retriever` protocol in
[`retrieval/interface.py`](../retrieval/interface.py):

- `BM25Index`: in-repository BM25 implementation;
- `VectorIndex`: dense cosine retrieval over persisted embeddings;
- `HybridRetriever`: reciprocal-rank fusion with `k=60`;
- `CrossEncoderReranker`: optional `sentence-transformers` cross-encoder,
  with an injected scorer supported for tests and a deterministic lexical
  fallback for local operation.

`RetrievalFilters` applies tenant and inclusive effective-date filters before
ranking. Missing effective dates do not pass a date-filtered query. The index
stores `effective_date` on every generated parent and child chunk where the
frozen audit provides a date.