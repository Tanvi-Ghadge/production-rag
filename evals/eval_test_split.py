"""
Run final evaluation of the winning configuration (+ctx_headers +rerank top50->10)
on the locked test split (n=36 answerable).
Run once at the very end.
Outputs: evals/results/test_eval.json
"""
import hashlib
import json
import math
import re
from pathlib import Path
from statistics import mean

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
        "configuration": name,
        "split": "test",
        "questions": n,
        "recall@5": round(mean(r5), 4),
        "recall@5_ci95": list(wilson_ci(hits5, n)),
        "recall@20": round(mean(r20), 4),
        "section_recall@5": round(mean(sec5), 4),
        "doc_recall@5": round(mean(doc5), 4),
        "span_recall@5": round(mean(span5), 4),
        "mrr": round(mean(mrr_vals), 4),
        "by_category_recall@5": {c: round(mean(v), 4) for c, v in sorted(by_cat.items())},
    }
    return out

print("Loading locked test split...", flush=True)
split = json.loads((ROOT / "evals/golden/split.json").read_text())
test_ids = set(split["test"])
golden_all = [json.loads(l) for l in (ROOT / "evals/golden/golden.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
golden_test = [r for r in golden_all if r["id"] in test_ids and r.get("answerable")]
print(f"Test split: {len(golden_test)} answerable questions", flush=True)

print("Loading documents...", flush=True)
documents = [
    json.loads(line) for line in (ROOT / "data/index/chunks.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip() and json.loads(line).get("kind") == "child"
]

class DiskCachedReranker:
    def __init__(self, model_name="BAAI/bge-reranker-base"):
        self._inner = CrossEncoderReranker(model_name=model_name)
        self.cache_path = CACHE / f"reranker-cache-{model_name.replace('/','_')}.json"
        self._cache: dict[str, float] = {}
        if self.cache_path.exists():
            try: self._cache = json.loads(self.cache_path.read_text())
            except: pass

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

print("Running test evaluation...", flush=True)
result = evaluate(
    "+ctx_headers +rerank top50->10",
    golden_test,
    lambda q: reranker.rerank(q, ctx_hybrid.retrieve(q, 50), 10),
)

out_file = RESULTS / "test_eval.json"
out_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
print("\n=== TEST SPLIT RESULT ===")
print(json.dumps(result, indent=2))
