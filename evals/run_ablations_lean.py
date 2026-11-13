"""
Lean ablation: only the configs needed for winning-config decision.
Reuses precomputed embeddings from chunks.jsonl and reranker cache.
Saves after every config. Skips bge-base (too slow on CPU).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from statistics import mean
from typing import Callable

ROOT = Path(__file__).parents[1]
RESULTS = ROOT / "evals" / "results"
CACHE = ROOT / "data" / "eval-cache"

from ingest.embedder import SentenceTransformerEmbedder
from retrieval.bm25 import BM25Index
from retrieval.dense import VectorIndex
from retrieval.hybrid import HybridRetriever
from retrieval.rerank import CrossEncoderReranker

_STOPWORDS = {
    "a","an","and","are","as","at","be","by","for","from","in","is","it",
    "of","on","or","that","the","this","to","was","were","what","which",
    "with","shall","will","under",
}

def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0: return (0.0, 0.0)
    p = k / n; z2n = z * z / n
    centre = (p + z2n / 2) / (1 + z2n)
    half = z * math.sqrt(p * (1 - p) / n + z2n / (4 * n)) / (1 + z2n)
    return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))

def _key_terms(text):
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2 and t not in _STOPWORDS}

def evaluate(name, golden, retrieve):
    answerable = [r for r in golden if r.get("answerable")]
    r5, r20, sec5, doc5, span5, mrr_vals = [], [], [], [], [], []
    by_cat = {}
    for row in answerable:
        passages = row.get("source_passages") or []
        gold_chunks = {str(p["chunk_id"]) for p in passages}
        # also accept valid_chunk_ids
        gold_chunks |= {str(c) for c in row.get("valid_chunk_ids", [])}
        gold_sections = {(str(p["document_id"]), str(p.get("section_path",""))) for p in passages}
        gold_docs = {str(p["document_id"]) for p in passages}
        ref_terms = _key_terms(str(row.get("reference_answer","")))

        results = retrieve(str(row["question"]))
        docs = [d for d, _ in results]
        cids = [str(d["chunk_id"]) for d in docs]
        secs = [(str(d["document_id"]), str(d.get("section_path",""))) for d in docs]
        dids = [str(d["document_id"]) for d in docs]

        r5.append(float(any(c in gold_chunks for c in cids[:5])))
        r20.append(float(any(c in gold_chunks for c in cids[:20])))
        sec5.append(float(any(s in gold_sections for s in secs[:5])))
        doc5.append(float(any(d in gold_docs for d in dids[:5])))
        combined = " ".join(str(d.get("text","")) for d in docs[:5])
        ret_terms = _key_terms(combined)
        span5.append(float(len(ref_terms & ret_terms) / max(1, len(ref_terms)) >= 0.5))
        mrr_vals.append(next((1.0/(i+1) for i,c in enumerate(cids) if c in gold_chunks), 0.0))
        cat = str(row.get("category","?"))
        by_cat.setdefault(cat, []).append(r5[-1])

    n = len(answerable)
    hits5 = int(sum(r5))
    out = {
        "configuration": name, "questions": n,
        "recall@5": round(mean(r5),4), "recall@5_ci95": list(wilson_ci(hits5, n)),
        "recall@20": round(mean(r20),4),
        "section_recall@5": round(mean(sec5),4),
        "doc_recall@5": round(mean(doc5),4),
        "span_recall@5": round(mean(span5),4),
        "mrr": round(mean(mrr_vals),4),
        "by_category_recall@5": {c: round(mean(v),4) for c,v in sorted(by_cat.items())},
    }
    return out

# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading dev split...", flush=True)
split = json.loads((ROOT / "evals/golden/split.json").read_text())
dev_ids = set(split["dev"])
golden_all = [json.loads(l) for l in (ROOT / "evals/golden/golden.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
golden = [r for r in golden_all if r["id"] in dev_ids]
print(f"Dev: {len(golden)} qs, {len([r for r in golden if r.get('answerable')])} answerable", flush=True)

print("Loading precomputed chunks...", flush=True)
documents = [
    json.loads(line) for line in (ROOT / "data/index/chunks.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip() and json.loads(line).get("kind") == "child"
]
print(f"Loaded {len(documents)} child chunks", flush=True)

embedder = SentenceTransformerEmbedder(CACHE / "embedding-cache-400-0.json", "BAAI/bge-small-en-v1.5")
bm25 = BM25Index(documents)
dense = VectorIndex(documents)
print("BM25 + VectorIndex built", flush=True)

# Reranker with disk cache
class DiskCachedReranker:
    def __init__(self, model_name="BAAI/bge-reranker-base"):
        self._inner = CrossEncoderReranker(model_name=model_name)
        self.cache_path = CACHE / f"reranker-cache-{model_name.replace('/','_')}.json"
        self._cache: dict[str, float] = {}
        if self.cache_path.exists():
            try: self._cache = json.loads(self.cache_path.read_text())
            except: pass
        print(f"Reranker cache loaded: {len(self._cache)} entries", flush=True)

    def _k(self, q, t):
        return hashlib.sha256(f"{q}\x00{t}".encode()).hexdigest()[:32]

    def rerank(self, query, candidates, top_k=10):
        if not candidates: return []
        missing = [(i, str(d["text"])) for i,(d,_) in enumerate(candidates) if self._k(query, str(d["text"])) not in self._cache]
        if missing:
            scores = list(self._inner.scorer([(query, t) for _,t in missing]))
            for (_,t), s in zip(missing, scores):
                self._cache[self._k(query, t)] = float(s)
            try: self.cache_path.write_text(json.dumps(self._cache))
            except: pass
        ranked = [(d, self._cache[self._k(query, str(d["text"]))]) for d,_ in candidates]
        return sorted(ranked, key=lambda x: x[1], reverse=True)[:top_k]

reranker = DiskCachedReranker()

# ── Load ctx embedder (precomputed) ───────────────────────────────────────────
print("Building contextual-header index...", flush=True)
ctx_docs = []
for doc in documents:
    copy = dict(doc)
    copy["text"] = f"[{doc['document_id']} > {doc.get('section_path','')}] {doc['text']}"
    ctx_docs.append(copy)
ctx_embedder = SentenceTransformerEmbedder(CACHE / "embedding-cache-ctx-400-0.json", "BAAI/bge-small-en-v1.5")
for doc, vec in zip(ctx_docs, ctx_embedder.embed(d["text"] for d in ctx_docs)):
    doc["embedding"] = vec
ctx_hybrid = HybridRetriever(BM25Index(ctx_docs), VectorIndex(ctx_docs), ctx_embedder, identifier_boost=0.0)
print("Done building ctx index", flush=True)

# ── Configs ───────────────────────────────────────────────────────────────────
results = []
def _eval(name, fn):
    row = evaluate(name, golden, fn)
    results.append(row)
    ci = row["recall@5_ci95"]
    print(f"{name:40s} R@5={row['recall@5']:.4f} [{ci[0]:.3f},{ci[1]:.3f}] Sec@5={row['section_recall@5']:.4f} Doc@5={row['doc_recall@5']:.4f} R@20={row['recall@20']:.4f}", flush=True)
    (RESULTS / "ablations_lean.json").write_text(json.dumps(results, indent=2))

base = HybridRetriever(bm25, dense, embedder, fusion_k=60, freshness_boost=0.002, identifier_boost=0.0)
id_h = HybridRetriever(bm25, dense, embedder, fusion_k=60, freshness_boost=0.002, identifier_boost=0.015)

_eval("bm25:400:0",                   lambda q: bm25.search(q, 50))
_eval("dense:400:0",                  lambda q: dense.search(embedder.embed([q])[0], 50))
_eval("hybrid (baseline)",            lambda q: base.retrieve(q, 50))
_eval("+identifier_boost",            lambda q: id_h.retrieve(q, 50))
_eval("hybrid +rerank top20->10",     lambda q: reranker.rerank(q, base.retrieve(q, 20), 10))
_eval("hybrid +rerank top50->10",     lambda q: reranker.rerank(q, base.retrieve(q, 50), 10))
_eval("+id_boost +rerank top50->10",  lambda q: reranker.rerank(q, id_h.retrieve(q, 50), 10))
_eval("+ctx_headers",                 lambda q: ctx_hybrid.retrieve(q, 50))
_eval("+ctx_headers +rerank top50->10", lambda q: reranker.rerank(q, ctx_hybrid.retrieve(q, 50), 10))

print("\n=== WINNER ===")
best = max(results, key=lambda r: r["recall@5"])
print(f"{best['configuration']} → R@5={best['recall@5']:.4f} CI95={best['recall@5_ci95']}", flush=True)
print("Done. Results in evals/results/ablations_lean.json")
