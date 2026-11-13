# Production RAG: Regulatory Compliance Engine

A Retrieval-Augmented Generation (RAG) service built with FastAPI, hybrid lexical + dense retrieval, cross-encoder reranking, multi-tenant isolation, multi-layer guardrails, caching, and per-stage tracing over a frozen corpus of Indian banking and payments regulations (RBI, NPCI, MeitY, and India Code).

---

## Overview

Regulatory compliance Q&A breaks naive-RAG pipelines in predictable ways:
- **Exact identifiers matter**: Circular numbers, section references (`Section 10(2)`), and acronyms (`KYC`, `AML`, `PPI`) are often missed by dense embeddings alone.
- **Older rules cannot be deleted**: Superseded guidelines are still needed for historical audits, so the retriever must prefer active directions without erasing older ones.
- **Context fragments lose legal exceptions**: Small chunks retrieve accurately, but answering from isolated snippets drops surrounding conditions and provisos.
- **Unsupported answers are unacceptable**: Queries outside the corpus or prompt-injection attempts must be refused or blocked with verifiable citations on valid answers.

---

## Architecture

```mermaid
flowchart TD
    subgraph Ingestion["Offline Ingestion (make ingest / pgvector-ingest)"]
        A[31 Regulatory PDFs<br/>Tenant A & B] --> B[PDF Layout Parser]
        B --> C[Structure-Aware Parent & Child Chunker<br/>Child: 400 words | Parent sections]
        C --> D[SHA-256 Content-Hash Cache<br/>Idempotent upsert]
        D --> E[BAAI/bge-small-en-v1.5<br/>384-dim embeddings]
        E --> F[(BM25 Index + Docker pgvector HNSW)]
    end

    subgraph Serving["Online Serving Pipeline (POST /v1/ask)"]
        G[Query + History + Tenant] --> H[Multi-Layer Input Guard<br/>PII Redaction, Injection, Hindi/Hinglish, Domain]
        H --> I[History-Aware Query Rewriter]
        I --> J[Hybrid Retrieval: BM25 + Dense<br/>RRF + Identifier & Freshness Boost]
        J --> K[Cross-Encoder Reranker<br/>Top 20-50 to Top 10]
        K --> L[Parent Expansion & Dedupe<br/>2,400-word context budget]
        L --> M[LLMClient<br/>Redis Cache, Circuit Breaker, Fallback]
        M --> N[Output Guard<br/>Citation Resolution & Schema Check]
        N --> O[SSE Token & Final JSON Stream]
    end
```

---

## What Was Built (AI & Backend Engineering)

### 1. Corpus & Idempotent Ingestion (`corpus/`, `ingest/`)
- **Frozen Corpus (`corpus-2026-11-09`)**: 31 public Indian regulatory PDFs split across two tenants (`A`: 18 docs / 1,983 chunks; `B`: 13 docs / 3,046 chunks; **5,029 total chunks**), including multi-version supersession chains (`pa_guidelines_2020` -> `pa_md_2025`, `kyc_md_2016` -> `kyc_md_2025`, `cyber_md_2024` -> `cyber_md_2026`, `ppi_md_2017` -> `ppi_md_2021`, and `emandate_2022` -> `2026`). See [docs/corpus.md](docs/corpus.md).
- **Structure-Aware Parent-Child Chunking**: Splits documents into section-level parent chunks and `400`-word child windows (`ingest/chunker.py`).
- **Content-Addressed Deduplication**: Chunks are hashed with SHA-256; re-running ingestion creates zero duplicate rows and skips unchanged embeddings.

### 2. Hybrid Retrieval, Freshness & Reranking (`retrieval/`)
- **Custom BM25 + Dense Vector Search**: Scratch-built BM25 index (`retrieval/bm25.py`) paired with `BAAI/bge-small-en-v1.5` (384-dim) stored in local vector index or PostgreSQL `pgvector` HNSW (`deploy/pgvector-init.sql`).
- **Reciprocal Rank Fusion (RRF) + Boosts**: Combines lexical and dense ranks (`retrieval/hybrid.py`) with a `+0.002` freshness boost for non-superseded documents and regex identifier boosting (`Section`, `Rule`, `Form`, circular IDs).
- **Metadata Isolation**: `tenant`, `effective_after`, and `effective_before` filters are applied at retrieval time (`SET LOCAL hnsw.ef_search = 80`) and re-enforced before parent assembly.
- **Cross-Encoder Reranking**: Reranks hybrid candidates down to top-10 (`retrieval/rerank.py`), with graceful skip if the reranker is unavailable.

### 3. Generation, Caching & Resilience (`query/`, `llm/`, `guard/`)
- **Context Assembly**: Expands selected child chunks to their parent sections, deduplicates overlapping parents, and caps context at `2,400` words (`query/assemble.py`).
- **XML-Delimited Grounding**: Retrieved chunks are wrapped in `<document chunk_id="...">` delimiters and treated strictly as untrusted data (`guard/context.py`).
- **Multi-Layer Guardrails**:
  - *Input (`guard/input_guard.py`, `guard/redact.py`)*: Redacts email, phone, Aadhaar, PAN, IFSC, and bank account numbers; blocks direct, jailbreak, delimiter, and Hindi/Hinglish prompt-injection patterns (`HTTP 422`); includes a second-layer borderline intent check (LLM-backed when `RAG_LLM_GUARD=1`, deterministic intent scoring offline); refuses out-of-domain queries (`refused: true`).
  - *Output (`guard/output_guard.py`)*: Enforces JSON schema validity and verifies every cited `chunk_id` resolves within the queried tenant's indexed chunks.
- **Resilient `LLMClient` (`llm/client.py`)**: Per-provider timeout (`30s`), exponential backoff retries with jitter, stateful circuit breaker (opens for `30s` after `3` consecutive failures), multi-provider fallback (`Foundry` / `Cohere command-r-08-2024` -> deterministic extractive fallback), Redis `ExactCache` (`llm/cache.py`), and optional in-memory `SemanticCache` (`RAG_SEMANTIC_CACHE=1`).

### 4. FastAPI Service & Startup Optimization (`app/`, `observability/`)
- **Endpoints (`app/main.py`)**: `POST /v1/ask` (SSE streaming), `POST /v1/ingest`, `GET /v1/ingest/{job_id}`, `POST /v1/feedback`, `GET /v1/health`.
- **Auth & Rate Limiting**: `X-API-Key` validation and sliding-window rate limiting (`60` req/min per key).
- **Lifespan Warm-up & Pooling**: Models, BM25 index, and pre-grouped tenant lookup dicts are loaded once in FastAPI `lifespan` with a startup warm-up query; `PgVectorRetriever` reuses a persistent thread-safe `psycopg` connection and in-memory LRU query embedding cache (`persist_cache=False` online) with `torch.set_num_threads(4)`.

---

## Performance & Latency (Before vs. After)

Profiling revealed that the initial `40.5 s` `retrieve` p50 and `1.9 s` `assemble` p50 were caused by lazy first-request loading of `SentenceTransformer` (`49.8 s`) and `chunks.jsonl` (`1.94 s`), plus per-request `psycopg.connect()` handshakes and synchronous disk cache writes.

### Steady-State Latency (`n = 200` queries, `10` warm-up discarded)

| Stage | Before p50 | Before p95 | After p50 | After p95 | Speedup (p50) |
|---|---:|---:|---:|---:|---:|
| `input_guard` | 0.70 ms | 1.46 ms | **0.12 ms** | **0.18 ms** | 5.8x |
| `rewrite` | 0.01 ms | 0.02 ms | **0.003 ms** | **0.004 ms** | 3.3x |
| `retrieve` | 40,493.51 ms | 55,121.58 ms | **58.98 ms** | **81.34 ms** | **686.5x** |
| `rerank` | — | — | **3.37 ms** | **5.87 ms** | — |
| `assemble` | 1,918.42 ms | 1,969.71 ms | **0.13 ms** | **0.29 ms** | **15,225x** |
| `generate` | 97.08 ms | 14,087.04 ms | **30.01 ms** | **3,003.51 ms** | 3.2x |
| **SSE TTFT** | — | — | **101.41 ms** | **3,073.93 ms** | — |
| **End-to-End Total** | **43,401.94 ms** | **61,399.07 ms** | **151.48 ms** | **3,206.40 ms** | **286.5x** |

- **Cold start** (isolated to FastAPI `lifespan` startup): `39,980.05 ms` ([evals/results/latency-after.json](evals/results/latency-after.json)).
- **Query embedding cache state**: The 200-query benchmark cycles through a pool of 25 sample questions 8 times (10 discarded warm-up), so the `58.98 ms` `retrieve` p50 is warm with respect to the in-memory query embedding cache.
- **Cache hit rate & framework gap**: `92.5%` exact cache hit rate (p95 reflects cold live Cohere API generation at `3,003.51 ms`). The 58.86 ms difference between individual stage sum (`92.62 ms`) and end-to-end wall-clock (`151.48 ms`) is not profiled; likely framework and streaming overhead.
- **pgvector `EXPLAIN ANALYZE`**: Verified `Index Scan using chunks_embedding_hnsw_idx` (`vector_cosine_ops` with `<=>`) executing in `2.03 ms`.

---

## Evaluation & Ablations

> [!IMPORTANT]
> **Evaluation audit (Phase 0 — completed 2026-11-13):** The original question set had 40/90 factoid questions that quoted section headings verbatim (e.g. `"what requirement is stated in '15.3 PPI issuers…'"`), which caused BM25 and contextual-headers retrieval to match via exact string overlap rather than semantic relevance. All 40 were rewritten as natural questions derived from gold passage text only (see [evals/golden/CHANGELOG.md](evals/golden/CHANGELOG.md)). The golden set was expanded from 120 to 160 total questions (130 answerable: 94 dev / 36 test, plus 15 unanswerable and 15 adversarial in dev) after hand-checking removed 5 malformed questions. Numbers below are from the **clean dev split** (`n=95` answerable at run time). The contaminated ablation table (Run 004 in [evals/results/results_log.md](evals/results/results_log.md)) is preserved but invalidated.
> 
> Generation metrics (faithfulness, correctness, citation, refusal) on the cleaned question set: **not measured**.

### 1. Multi-Level Retrieval & Ablation Matrix (95 Dev Questions, Clean Set)

Evaluated on the frozen dev split (`n=95` answerable) with heading-leakage eliminated. Primary metric (`Recall@5`) includes 95% Wilson confidence intervals ([evals/results/ablations.md](evals/results/ablations.md), [evals/results/ablations_lean.json](evals/results/ablations_lean.json)):

| Configuration | R@5 (Chunk) | 95% Wilson CI | Sec@5 | Doc@5 | Span@5 | R@20 | MRR |
|---|---:|:---:|---:|---:|---:|---:|---:|
| `dense:400:0` (`bge-small`) | 0.5053 | [0.406, 0.604] | 0.5053 | 0.8105 | 0.5263 | 0.5895 | 0.3932 |
| `hybrid (baseline)` | 0.6211 | [0.521, 0.712] | 0.6211 | 0.8947 | 0.6526 | 0.6947 | 0.4611 |
| `bm25:400:0` | 0.6632 | [0.563, 0.750] | 0.6632 | 0.9158 | 0.6526 | 0.7579 | 0.5704 |
| `+identifier_boost` | 0.6526 | [0.553, 0.741] | 0.6526 | 0.9474 | 0.6842 | 0.7789 | 0.5259 |
| `hybrid +rerank top20->10` | 0.6000 | [0.499, 0.693] | 0.6000 | 0.8842 | 0.6316 | 0.6316 | 0.4507 |
| `hybrid +rerank top50->10` | 0.5895 | [0.489, 0.683] | 0.5895 | 0.9368 | 0.6316 | 0.6211 | 0.4393 |
| `+id_boost +rerank top50->10` | 0.6105 | [0.510, 0.703] | 0.6105 | 0.9579 | 0.6526 | 0.6632 | 0.4586 |
| `+ctx_headers` | 0.6421 | [0.542, 0.731] | 0.6421 | 0.9053 | 0.6316 | 0.7263 | 0.5122 |
| **`+ctx_headers +rerank top50->10` (WINNER)** | **0.7474** | **[0.652, 0.824]** | **0.7474** | **0.9789** | **0.7368** | **0.7684** | **0.6575** |

**Category breakdown of winning configuration (`+ctx_headers +rerank top50->10`):**
- `factoid` (`n=35`): **0.9143** (`32/35`)
- `table_lookup` (`n=21`): **0.8095** (`17/21`)
- `multi_hop` (`n=21`): **0.6190** (`13/21`)
- `version_sensitive` (`n=18`): **0.5000** (`9/18`)

**Key engineering findings (including negative results):**
- **Contextual headers enable rerankers**: Without contextual headers, vanilla cross-encoder reranking slightly lowered strict chunk `R@5` (`0.6211` -> `0.5895`) because the reranker penalizes short regulatory fragments that lack document context. Prepending `[document_id > section_path]` resolved this ambiguity, unlocking the top score of **`0.7474`** (`+12.6pp` over baseline hybrid, `+24.2pp` over dense alone).
- **BM25 outperforms naive dense & hybrid**: BM25 alone hits `0.6632` vs. `0.5053` for `bge-small` dense search and `0.6211` for baseline hybrid (from [evals/results/ablations_lean.json](evals/results/ablations_lean.json)). In Indian regulatory compliance, exact legal identifiers (`Section 10(2)`, `V-CIP`, `PPI`, `TPAP`) carry high lexical discriminative power that small dense models dilute.
- **Selection rule execution (D-001) & Test verification**: The winning configuration was selected from nine configurations evaluated on dev by dev `Recall@5` (`0.7474`, 95% CI `[0.6516, 0.8240]`). Notice that the dev confidence intervals of the winner and BM25 alone (`0.6632`, `[0.5634, 0.7502]`) overlap. Evaluated once on the locked test split (`n=36` answerable, [evals/results/test_eval.json](evals/results/test_eval.json)), the winning configuration achieved **`Recall@5 = 0.7500`** [95% Wilson CI: `0.5893, 0.8625`] (`27/36`), `MRR = 0.6655`, and `Doc@5 = 0.9722`, confirming generalization without dev overfitting.

### 2. Legacy 120-Question Run (Pre-Audit, Not Rerun)

*Note: Evaluated on the pre-audit question set on 2026-11-11; generation metrics have not been rerun on the cleaned dev split.*

From [evals/results/answers.json](evals/results/answers.json) and [evals/results/calibration.json](evals/results/calibration.json):

| Category | Questions | Faithfulness | Correctness | Refusal Acc. | Citation Acc. |
|---|---:|---:|---:|---:|---:|
| `factoid` | 40 | 1.0000 | 0.3969 | 1.0000 | 0.6000 |
| `multi_hop` | 20 | 0.9000 | 0.2551 | 1.0000 | 0.5000 |
| `table_lookup` | 15 | 1.0000 | 0.2260 | 1.0000 | 0.2667 |
| `version_sensitive` | 15 | 1.0000 | 0.5561 | 1.0000 | 0.6000 |
| `unanswerable` | 15 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `adversarial` | 15 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **Overall (120)** | **120** | **0.9833** | **0.5226** | **1.0000** | **0.6417** |

**Failure analysis on the 58 `incorrect` answers (legacy pre-audit run):**
- `45` (`77.6%`) — Right document cited, neighbor/section chunk mismatch or strict lexical penalty (`39/58` were scored by `lexical_fallback` rather than the LLM judge).
- `10` (`17.2%`) — True retrieval miss (`table_lookup` and `multi_hop` are the weakest categories).
- `3` (`5.2%`) — Wrong/superseded document version cited.

**Judge calibration (`evals/calibrate.py`):**
- Legacy 30-item F1/similarity check: `1.00` faithful agreement (`kappa=1.0`), `0.4333` correctness agreement (`kappa=0.0`).
- **Key-facts rubric (65 items, 2–4 required facts per question)**: `1.0000` faithful agreement (uninformative because all 65/65 labeled items in calibration.json are faithful), **`0.8154`** correctness agreement (**`kappa=0.5522`**, moderate agreement).

### 3. Guardrails, Red-Team & False-Positive Evaluation

From [evals/results/redteam.md](evals/results/redteam.md) and [evals/results/redteam-after.json](evals/results/redteam-after.json) (`59` total suite cases: `45` adversarial attack probes, `14` failure/resilience test cases, plus `100` benign queries): **0 of 45 attacks succeeded, 1 of 100 benign queries blocked**.

| Stage | Attack Success Rate | Benign False-Positive Rate (`n=100`) |
|---|---:|---:|
| Before guardrails | 100.00% | 0.00% |
| Legacy single-regex baseline | 62.22% | 0.00% |
| **After multi-layer guardrails** | **0.00%** | **1.00%** (1/100) |

- **Failure modes** ([evals/results/failure-modes.json](evals/results/failure-modes.json)): `5/5` passed (Cohere, Redis, pgvector, reranker outages, malformed provider output).
- **Tenant isolation**: 40-query cross-tenant probe and local pgvector (`5,029` rows) confirmed zero cross-tenant chunk leakage.

---

## Setup & Usage

```bash
git clone https://github.com/Tanvi-Ghadge/production-rag.git
cd production-rag

python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Linux/macOS:        source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
docker compose -f deploy/docker-compose.pgvector.yml up -d

# Ingest local index and pgvector embeddings
python -m ingest.run
python -m ingest.pgvector_run

# Start API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Verification & Benchmarks

```bash
python -m evals.ci_gate                  # CI regression gate
python -m redteam.run                    # 59-case red-team + 100-query FPR
python -m evals.calibrate                # 65-item key-facts judge calibration + Cohen's kappa
python -m observability.benchmark_latency # 200-query steady-state latency + TTFT
python -m evals.run_ablations            # Multi-level retrieval + Track C ablations
pytest -v tests                          # Unit & integration tests
```

---

## Repository Structure

```text
├── app/                # FastAPI service (lifespan warmup, routes, auth, rate limiting)
├── corpus/             # 31 public Indian regulatory PDFs (Tenants A & B) and manifest
├── data/index/         # Content-addressed index, BM25 index, and embedding cache
├── deploy/             # Dockerfile, pgvector + Redis compose stack, Azure notes
├── docs/               # Corpus policy, decisions log, failure modes, architecture notes
├── evals/              # Golden set (160 questions, dev/test split), ablations, key-facts judge, CI gate
├── guard/              # PII redaction, multi-layer injection/domain checks, output guard
├── ingest/             # PDF parser, parent-child chunker, embedder, pgvector & local indexers
├── llm/                # LLMClient (circuit breaker, retries, fallback), Redis & semantic caches
├── observability/      # Per-stage tracing, percentile reporting, steady-state benchmark
├── query/              # Query rewriter/expander, parent context assembly, generation
├── redteam/            # 59-case adversarial suite + 100 benign query FPR benchmark
└── tests/              # API, ingestion, retrieval, guardrail, and pgvector contract tests
```

---

## Verification summary

All 9 acceptance criteria verified against repo artifacts:

| # | Acceptance Test | Verification Status | Artifact / Evidence |
|---|---|:---:|---|
| 1 | Idempotent Ingestion & Retrieval Ablations | **PASS** | `ingest/indexer.py` SHA-256 dedupe skips existing chunks; `tests/test_week7_ingestion.py` passes (`changed == 0`); [evals/results/ablations.md](evals/results/ablations.md) |
| 2 | `/v1/ask` Citations & Refusals | **PASS** | Output guard validates citations against queried tenant; legacy pre-audit run achieved 1.0000 refusal accuracy and 0.6417 citation accuracy ([evals/results/answers.json](evals/results/answers.json)); clean set generation: not measured |
| 3 | Tenant Isolation | **PASS** | 40-query cross-tenant probe; zero chunk leakage between Tenant A (1,983 chunks) and Tenant B (3,046 chunks) |
| 4 | Version Sensitivity | **KNOWN WEAKNESS** | 50.0% newest document preference on clean dev version queries (9/18). Retriever still retrieves superseded passages when lexical matches are strong ([evals/results/ablations_lean.json](evals/results/ablations_lean.json)) |
| 5 | Red-Team Suite & Attack Metrics | **PASS** | Attack success rate reduced from **100.00%** to **0.00%** (0 of 45 attacks succeeded, 1 of 100 benign queries blocked) ([evals/results/redteam.md](evals/results/redteam.md)) |
| 6 | LLM Fallback & Circuit Breaker | **PASS** | 30s timeout, exponential backoff, circuit breaker opens after 3 failures with deterministic fallback ([evals/results/failure-modes.json](evals/results/failure-modes.json)) |
| 7 | Latency Breakdown & Cache Hit Rate | **PASS** | Steady-state p50 = 151.5 ms (embedding cache warm), p95 = 3,206.4 ms; retrieve p50 = 59.0 ms, assemble p50 = 0.13 ms; 92.5% cache hit rate ([evals/results/latency-after.json](evals/results/latency-after.json)) |
| 8 | Judge Calibration & Labeled Set | **PASS** | Key-facts rubric on 65 labeled items achieves **0.8154** correctness agreement (**kappa = 0.5522**, moderate); faithfulness agreement = **1.0000** (uninformative, all 65/65 faithful) ([evals/results/calibration.json](evals/results/calibration.json)) |
| 9 | CI Regression Gate | **PASS** | `python -m evals.ci_gate` enforces max 3pp drop on Recall@5 (passing at Recall@5 = 0.7474); legacy answer gate passed at faithfulness = 0.9833 |

