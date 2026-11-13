"""Track B1/B2/B5 multi-level retrieval evaluation & Track C ablations.

Runs on the DEV split only. Test split is locked until final config selection.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from statistics import mean
from typing import Callable

from evals.run_retrieval import (
    CACHE,
    RESULTS,
    load_documents,
    load_golden,
    version_rate,
)
from ingest.embedder import SentenceTransformerEmbedder
from query.rewrite import expand_query
from retrieval.bm25 import BM25Index
from retrieval.dense import VectorIndex
from retrieval.hybrid import HybridRetriever
from retrieval.rerank import CrossEncoderReranker

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "was", "were", "what", "which", "with", "shall", "will", "under",
}


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson confidence interval for a proportion k/n."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    z2n = z * z / n
    centre = (p + z2n / 2) / (1 + z2n)
    half = z * math.sqrt(p * (1 - p) / n + z2n / (4 * n)) / (1 + z2n)
    return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))


def _key_terms(text: str) -> set[str]:
    return {
        t for t in re.findall(r"[a-z0-9]+", text.lower())
        if len(t) > 2 and t not in _STOPWORDS
    }


def _ndcg(hits: list[bool], ideal_hits: int) -> float:
    if ideal_hits <= 0:
        return 0.0
    dcg = sum((1.0 / math.log2(i + 2)) for i, h in enumerate(hits) if h)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / ideal


def evaluate_multilevel(
    name: str,
    golden: list[dict[str, object]],
    retrieve: Callable[[str], list[tuple[dict[str, object], float]]],
) -> dict[str, object]:
    answerable = [r for r in golden if r.get("answerable")]
    metrics: dict[str, list[float]] = {
        "recall@5": [], "recall@10": [], "recall@20": [], "recall@50": [],
        "mrr": [], "ndcg@5": [], "ndcg@10": [],
        "section_recall@5": [], "section_recall@10": [],
        "doc_recall@5": [], "doc_recall@10": [],
        "span_recall@5": [], "span_recall@10": [],
    }
    by_category: dict[str, list[float]] = {}

    for row in answerable:
        passages = row.get("source_passages") or []
        gold_chunks = {str(p["chunk_id"]) for p in passages}
        gold_sections = {(str(p["document_id"]), str(p.get("section_path", ""))) for p in passages}
        gold_docs = {str(p["document_id"]) for p in passages}
        ref_terms = _key_terms(str(row.get("reference_answer", "")))

        results = retrieve(str(row["question"]))
        docs = [doc for doc, _ in results]
        chunk_ids = [str(d["chunk_id"]) for d in docs]
        sections = [(str(d["document_id"]), str(d.get("section_path", ""))) for d in docs]
        doc_ids = [str(d["document_id"]) for d in docs]

        for k in (5, 10, 20, 50):
            metrics[f"recall@{k}"].append(float(any(cid in gold_chunks for cid in chunk_ids[:k])))

        for k in (5, 10):
            hits = [cid in gold_chunks for cid in chunk_ids[:k]]
            metrics[f"ndcg@{k}"].append(_ndcg(hits, min(len(gold_chunks), k)))
            metrics[f"section_recall@{k}"].append(float(any(s in gold_sections for s in sections[:k])))
            metrics[f"doc_recall@{k}"].append(float(any(did in gold_docs for did in doc_ids[:k])))
            combined_text = " ".join(str(d.get("text", "")) for d in docs[:k])
            ret_terms = _key_terms(combined_text)
            containment = len(ref_terms & ret_terms) / max(1, len(ref_terms))
            metrics[f"span_recall@{k}"].append(float(containment >= 0.5))

        mrr = next((1.0 / (i + 1) for i, cid in enumerate(chunk_ids) if cid in gold_chunks), 0.0)
        metrics["mrr"].append(mrr)
        cat = str(row.get("category", "unknown"))
        by_category.setdefault(cat, []).append(float(any(cid in gold_chunks for cid in chunk_ids[:5])))

    out: dict[str, object] = {"configuration": name, "questions": len(answerable)}
    for k, vals in metrics.items():
        mean_val = round(mean(vals), 4) if vals else 0.0
        out[k] = mean_val
        # Add Wilson CI for binary (0/1) metrics
        if vals and all(v in (0.0, 1.0) for v in vals):
            hits = int(sum(vals))
            lo, hi = wilson_ci(hits, len(vals))
            out[f"{k}_ci95"] = [lo, hi]
    out["by_category_recall@5"] = {cat: round(mean(vals), 4) for cat, vals in sorted(by_category.items())}
    return out


class CachedReranker:
    """Caches (query, text) scores across ablation runs to avoid redundant CPU work."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base") -> None:
        self._inner = CrossEncoderReranker(model_name=model_name)
        self._cache: dict[tuple[str, str], float] = {}

    def rerank(
        self,
        query: str,
        candidates: list[tuple[dict[str, object], float]],
        top_k: int = 10,
    ) -> list[tuple[dict[str, object], float]]:
        if not candidates:
            return []
        missing = [
            (i, str(doc["text"]))
            for i, (doc, _) in enumerate(candidates)
            if (query, str(doc["text"])) not in self._cache
        ]
        if missing:
            pairs = [(query, text) for _, text in missing]
            scores = list(self._inner.scorer(pairs))
            for (_, text), score in zip(missing, scores):
                self._cache[(query, text)] = float(score)
        ranked = [(doc, self._cache[(query, str(doc["text"]))]) for doc, _ in candidates]
        return sorted(ranked, key=lambda item: item[1], reverse=True)[:top_k]


def _rrf_expand(hybrid: HybridRetriever, query: str, top_k: int = 50) -> list[tuple[dict[str, object], float]]:
    variants = expand_query(query)
    merged: dict[str, tuple[dict[str, object], float]] = {}
    for variant in variants:
        for rank, (doc, _) in enumerate(hybrid.retrieve(variant, top_k=top_k), start=1):
            cid = str(doc["chunk_id"])
            prev = merged.get(cid)
            merged[cid] = (doc, (prev[1] if prev else 0.0) + 1.0 / (60 + rank))
    return sorted(merged.values(), key=lambda x: x[1], reverse=True)[:top_k]


def run() -> list[dict[str, object]]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    golden_all = load_golden()

    # ── Filter to dev split only (test is locked) ──────────────────────────────
    split_path = Path("evals/golden/split.json")
    if split_path.exists():
        split = json.loads(split_path.read_text(encoding="utf-8"))
        dev_ids = set(split["dev"])
        golden = [r for r in golden_all if r["id"] in dev_ids]
        print(f"Dev split: {len(golden)} questions ({len([r for r in golden if r.get('answerable')])} answerable)")
    else:
        golden = golden_all
        print(f"No split.json found — using all {len(golden)} questions")

    reranker = CachedReranker("BAAI/bge-reranker-base")

    documents, embedder = load_documents(400, 0, "BAAI/bge-small-en-v1.5", False)
    bm25 = BM25Index(documents)
    dense = VectorIndex(documents)

    results: list[dict[str, object]] = []

    def _eval(name: str, fn: Callable[[str], list[tuple[dict[str, object], float]]]) -> None:
        row = evaluate_multilevel(name, golden, fn)
        row["version_citation_rate"] = version_rate(documents, golden, fn)
        results.append(row)
        print(
            f"{name:34s} R@5={row['recall@5']:.4f} Sec@5={row['section_recall@5']:.4f} "
            f"Doc@5={row['doc_recall@5']:.4f} Span@5={row['span_recall@5']:.4f} "
            f"R@20={row['recall@20']:.4f} R@50={row['recall@50']:.4f} Ver={row['version_citation_rate']:.4f}"
        )

    # 1. Baseline & Track B1 multi-level metrics
    base_hybrid = HybridRetriever(bm25, dense, embedder, fusion_k=60, freshness_boost=0.002, identifier_boost=0.0)
    _eval("bm25:400:0", lambda q: bm25.search(q, 50))
    _eval("dense:400:0", lambda q: dense.search(embedder.embed([q])[0], 50))
    _eval("hybrid:400:0 (baseline)", lambda q: base_hybrid.retrieve(q, 50))
    _eval("hybrid_reranker:top20->10 (base)", lambda q: reranker.rerank(q, base_hybrid.retrieve(q, 20), 10))
    _eval("hybrid_reranker:top40->10", lambda q: reranker.rerank(q, base_hybrid.retrieve(q, 40), 10))
    _eval("hybrid_reranker:top50->10", lambda q: reranker.rerank(q, base_hybrid.retrieve(q, 50), 10))

    # 2. Track C ablations (single change vs base_hybrid)
    id_hybrid = HybridRetriever(bm25, dense, embedder, fusion_k=60, freshness_boost=0.002, identifier_boost=0.015)
    _eval("+identifier_boost (hybrid)", lambda q: id_hybrid.retrieve(q, 50))
    _eval("+identifier_boost +rerank50", lambda q: reranker.rerank(q, id_hybrid.retrieve(q, 50), 10))

    _eval("+query_expansion (hybrid)", lambda q: _rrf_expand(base_hybrid, q, 50))

    for k in (20, 100):
        h_k = HybridRetriever(bm25, dense, embedder, fusion_k=k, freshness_boost=0.002, identifier_boost=0.0)
        _eval(f"fusion_k={k} (hybrid)", lambda q, h=h_k: h.retrieve(q, 50))

    h_bm25 = HybridRetriever(bm25, dense, embedder, bm25_weight=1.5, dense_weight=1.0, identifier_boost=0.0)
    _eval("weighted_rrf 1.5:1.0 (hybrid)", lambda q: h_bm25.retrieve(q, 50))

    h_dense = HybridRetriever(bm25, dense, embedder, bm25_weight=1.0, dense_weight=1.5, identifier_boost=0.0)
    _eval("weighted_rrf 1.0:1.5 (hybrid)", lambda q: h_dense.retrieve(q, 50))

    h_nofresh = HybridRetriever(bm25, dense, embedder, freshness_boost=0.0, identifier_boost=0.0)
    _eval("no_freshness_boost (hybrid)", lambda q: h_nofresh.retrieve(q, 50))

    # 3. Contextual chunk headers: prepend [Document | Section] before BM25 + dense
    ctx_docs = []
    for doc in documents:
        copy = dict(doc)
        copy["text"] = f"[{doc['document_id']} > {doc.get('section_path', '')}] {doc['text']}"
        ctx_docs.append(copy)
    ctx_embedder = SentenceTransformerEmbedder(CACHE / "embedding-cache-ctx-400-0.json", "BAAI/bge-small-en-v1.5")
    for doc, vec in zip(ctx_docs, ctx_embedder.embed(d["text"] for d in ctx_docs)):
        doc["embedding"] = vec
    ctx_hybrid = HybridRetriever(BM25Index(ctx_docs), VectorIndex(ctx_docs), ctx_embedder, identifier_boost=0.0)
    _eval("+contextual_headers (hybrid)", lambda q: ctx_hybrid.retrieve(q, 50))
    _eval("+contextual_headers +rerank50", lambda q: reranker.rerank(q, ctx_hybrid.retrieve(q, 50), 10))

    # 4. Stronger embedder: BAAI/bge-base-en-v1.5
    try:
        base_docs, base_emb = load_documents(400, 0, "BAAI/bge-base-en-v1.5", False)
        bge_base_hybrid = HybridRetriever(BM25Index(base_docs), VectorIndex(base_docs), base_emb, identifier_boost=0.0)
        _eval("embedder:bge-base (dense)", lambda q: VectorIndex(base_docs).search(base_emb.embed([q])[0], 50))
        _eval("embedder:bge-base (hybrid)", lambda q: bge_base_hybrid.retrieve(q, 50))
    except Exception as exc:
        print(f"Skipping bge-base-en-v1.5: {exc}")

    (RESULTS / "ablations.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    lines = [
        "# Multi-Level Retrieval & Track C Ablations (90 Answerable Questions)",
        "",
        "| Configuration | R@5 (Chunk) | Sec@5 | Doc@5 | Span@5 | R@10 | R@20 | R@50 | MRR | nDCG@5 | Ver. Pref |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        lines.append(
            f"| {r['configuration']} | {r['recall@5']:.4f} | {r['section_recall@5']:.4f} | "
            f"{r['doc_recall@5']:.4f} | {r['span_recall@5']:.4f} | {r['recall@10']:.4f} | "
            f"{r['recall@20']:.4f} | {r['recall@50']:.4f} | {r['mrr']:.4f} | {r['ndcg@5']:.4f} | {r['version_citation_rate']:.4f} |"
        )
    (RESULTS / "ablations.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return results


if __name__ == "__main__":
    run()
