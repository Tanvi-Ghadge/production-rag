# Evaluation Results Log

Every row is an evaluation run. Config, git-equivalent state, metric, and outcome.
Numbers without a source file are marked NOT MEASURED.

---

## Run 001 — 2026-11-09 (Before latency fix)
- **Config**: baseline hybrid, bge-small, chunk=400, no rerank, no headers
- **Data**: 90 answerable questions (original set, CONTAMINATED — 40 factoid quoted headings)
- **Source**: `evals/results/latency.json`
- **retrieve p50**: 40,493 ms — BROKEN (lazy model loading per request)
- **assemble p50**: 1,918 ms — BROKEN (per-request disk read)
- **Outcome**: FAIL — latency bugs found and fixed

## Run 002 — 2026-11-12 (Latency after fix)
- **Config**: baseline hybrid, bge-small, chunk=400, rerank top20→10, lifespan warm-up, connection pool
- **Data**: 200-query steady-state benchmark, 10 warm-up discarded
- **Source**: `evals/results/latency-after.json`
- **Cache hit rate**: 92.5% (cache-warm numbers below)
- **retrieve p50**: 58.98 ms | p95: 81.34 ms
- **assemble p50**: 0.13 ms | p95: 0.29 ms
- **generate p50**: 30.01 ms (Redis hit) | p95: 3,003.51 ms (live Cohere)
- **end-to-end p50**: 151.48 ms | p95: 3,206.40 ms (cache-warm)
- **TTFT p50**: 101.41 ms | p95: 3,073.93 ms
- **stage_sum p50**: 92.62 ms
- **overhead (ASGI+SSE)**: 58.86 ms (documented in latency-after.json)
- **cold_start**: 39,980 ms (FastAPI lifespan — isolated, not in steady-state)
- **Outcome**: PASS — targets met (retrieve <300ms, assemble <50ms)

## Run 003 — 2026-11-12 (Red-team, contaminated question set)
- **Config**: full pipeline, multi-layer guardrails
- **Data**: 59 adversarial + 100 benign queries
- **Source**: `evals/results/redteam-after.json`, `evals/results/redteam.md`
- **Attack success rate**: 0.00% (59/59 blocked)
- **Benign FPR**: 1.00% (1/100)
- **Outcome**: PASS

## Run 004 — 2026-11-12 (Ablations, CONTAMINATED question set — DO NOT USE AS HEADLINE)
- **Config**: 18 configurations on 90 questions (40 factoid contaminated with heading leakage)
- **Source**: `evals/results/ablations.json` (old), `evals/results/ablations.md` (old)
- **KNOWN ISSUE**: 40/90 factoid questions quoted section headings verbatim → inflated factoid R@5
- **Inflated headline**: +contextual_headers +rerank50 R@5 = 0.8556 (DO NOT CITE)
- **Clean estimate**: leakage-free factoid R@5 likely ~0.44 baseline → ~0.76 with headers+rerank
- **Outcome**: INVALIDATED — superseded by Run 005

## Run 005 — 2026-11-13 (Ablations, CLEAN dev split — COMPLETE)
- **Config**: 9 key configurations on 95 dev-split answerable questions (40 factoid rewritten naturally, heading leakage eliminated)
- **Source**: `evals/results/ablations_lean.json`
- **Split**: `evals/golden/split.json` — dev split only, seed=42, n=95 answerable
- **Results**:
  - `bm25:400:0`: Recall@5 = 0.6632 [95% CI: 0.5634, 0.7502], Recall@20 = 0.7579, Doc@5 = 0.9158
  - `dense:400:0`: Recall@5 = 0.5053 [95% CI: 0.4065, 0.6036], Recall@20 = 0.5895, Doc@5 = 0.8105
  - `hybrid (baseline)`: Recall@5 = 0.6211 [95% CI: 0.5206, 0.7121], Recall@20 = 0.6947, Doc@5 = 0.8947
  - `+identifier_boost`: Recall@5 = 0.6526 [95% CI: 0.5526, 0.7408], Recall@20 = 0.7789, Doc@5 = 0.9474
  - `hybrid +rerank top20->10`: Recall@5 = 0.6000 [95% CI: 0.4995, 0.6928], Recall@20 = 0.6316, Doc@5 = 0.8842
  - `hybrid +rerank top50->10`: Recall@5 = 0.5895 [95% CI: 0.4890, 0.6830], Recall@20 = 0.6211, Doc@5 = 0.9368
  - `+id_boost +rerank top50->10`: Recall@5 = 0.6105 [95% CI: 0.5100, 0.7025], Recall@20 = 0.6632, Doc@5 = 0.9579
  - `+ctx_headers`: Recall@5 = 0.6421 [95% CI: 0.5419, 0.7313], Recall@20 = 0.7263, Doc@5 = 0.9053
  - **`+ctx_headers +rerank top50->10` (WINNER)**: Recall@5 = **0.7474** [95% CI: **0.6516, 0.8240**], Recall@20 = **0.7684**, Doc@5 = **0.9789**, MRR = **0.6575**
- **Outcome**: WINNER SELECTED per D-001 rule (`+ctx_headers +rerank top50->10`).

## Run 006 — 2026-11-13 (CI gate on clean dev set — PASS)
- **Command**: `python -m evals.ci_gate`
- **Committed baseline**: `evals/results/baseline.json` (Recall@5 = 0.7474)
- **Output**: `{'recall@5': 0.7474, 'faithfulness': 0.9833, 'citation_accuracy': 0.6417, 'refusal_accuracy': 1.0}`
- **Outcome**: PASS (all regression thresholds satisfied)

## Run 007 — 2026-11-13 (Locked test split — final verification)
- **Command**: `python -m evals.eval_test_split`
- **Config**: Winning config `+ctx_headers +rerank top50->10`
- **Split**: `evals/golden/split.json` — test split only, locked, n=36 answerable
- **Output File**: `evals/results/test_eval.json`
- **Results**:
  - Recall@5 = **0.7500** [95% Wilson CI: **0.5893, 0.8625**] (27/36)
  - Recall@20 = **0.7778**
  - Section Recall@5 = **0.7778**
  - Document Recall@5 = **0.9722**
  - Span Recall@5 = **0.7500**
  - MRR = **0.6655**
  - Category breakdown:
    - factoid: 0.9286 (13/14)
    - multi_hop: 0.7778 (7/9)
    - table_lookup: 0.6667 (4/6)
    - version_sensitive: 0.4286 (3/7)
- **Outcome**: Confirms dev performance (dev 0.7474 vs test 0.7500). Generalization holds with no degradation on unseen test questions.
