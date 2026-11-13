from __future__ import annotations

import csv
from datetime import datetime
import json
from pathlib import Path
import argparse
from statistics import mean
from typing import Callable

from ingest.chunker import structure_aware_chunks
from ingest.embedder import HashEmbedder, SentenceTransformerEmbedder
from ingest.parsers.pdf import parse_pdf
from retrieval.bm25 import BM25Index
from retrieval.dense import VectorIndex
from retrieval.hybrid import HybridRetriever
from retrieval.rerank import CrossEncoderReranker


ROOT = Path(__file__).parents[1]
GOLDEN = ROOT / "evals" / "golden" / "golden.jsonl"
AUDIT = ROOT / "corpus" / "audit.csv"
CORPUS = ROOT / "corpus" / "raw"
RESULTS = ROOT / "evals" / "results"
CACHE = ROOT / "data" / "eval-cache"
VERSION_RELATIONSHIPS = {
    "pa_guidelines_2020.pdf": (None, "pa_md_2025.pdf"), "pa_circular_2021.pdf": (None, "pa_md_2025.pdf"),
    "pa_md_2025.pdf": ("pa_guidelines_2020.pdf", None), "kyc_md_2016.pdf": (None, "kyc_md_2025.pdf"),
    "kyc_md_2025.pdf": ("kyc_md_2016.pdf", None), "cyber_md_2024.pdf": (None, "cyber_md_2026.pdf"),
    "cyber_md_2026.pdf": ("cyber_md_2024.pdf", None), "ppi_md_2017.pdf": (None, "ppi_md_2021.pdf"),
    "ppi_md_2021.pdf": ("ppi_md_2017.pdf", None), "emandate_2022.pdf": (None, "emandate_2023.pdf"),
    "emandate_2023.pdf": ("emandate_2022.pdf", "emandate_2024.pdf"),
    "emandate_2024.pdf": ("emandate_2023.pdf", "emandate_framework_2026.pdf"),
    "emandate_framework_2026.pdf": ("emandate_2024.pdf", None),
}


def load_golden() -> list[dict[str, object]]:
    return [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines()]


def load_documents(
    child_words: int,
    overlap_words: int,
    model_name: str,
    use_hash: bool,
) -> tuple[list[dict[str, object]], HashEmbedder | SentenceTransformerEmbedder]:
    documents: list[dict[str, object]] = []
    with AUDIT.open(encoding="utf-8", newline="") as file:
        rows = csv.DictReader(file)
        for row in rows:
            path = CORPUS / row["tenant"] / row["file"]
            parsed = parse_pdf(path)
            if not parsed.text:
                continue
            chunks = structure_aware_chunks(
                parsed,
                f"{row['tenant']}:{path.stem}",
                row["tenant"],
                child_words=child_words,
                overlap_words=overlap_words,
                effective_date=_effective_date(row),
                supersedes=VERSION_RELATIONSHIPS.get(row["file"], (None, None))[0],
                superseded_by=VERSION_RELATIONSHIPS.get(row["file"], (None, None))[1],
            )
            documents.extend(chunk.to_dict() for chunk in chunks if chunk.kind == "child")
    embedder = (
        HashEmbedder(CACHE / f"hash-embedding-cache-{child_words}-{overlap_words}.json")
        if use_hash
        else SentenceTransformerEmbedder(
            CACHE / f"embedding-cache-{child_words}-{overlap_words}.json",
            model_name,
        )
    )
    for document, vector in zip(documents, embedder.embed(document["text"] for document in documents)):
        document["embedding"] = vector
    return documents, embedder


def evaluate_configuration(
    name: str,
    documents: list[dict[str, object]],
    golden: list[dict[str, object]],
    retrieve: Callable[[str], list[tuple[dict[str, object], float]]],
) -> dict[str, object]:
    answerable = [record for record in golden if record["answerable"]]
    metrics = {f"{metric}@{cutoff}": [] for metric in ("recall", "ndcg") for cutoff in (5, 10)}
    metrics["mrr"] = []
    for record in answerable:
        relevant = {str(passage["chunk_id"]) for passage in record["source_passages"]}
        results = retrieve(str(record["question"]))
        keys = [str(doc["chunk_id"]) for doc, _ in results]
        for cutoff in (5, 10):
            hits = [key in relevant for key in keys[:cutoff]]
            metrics[f"recall@{cutoff}"].append(float(any(hits)))
            metrics[f"ndcg@{cutoff}"].append(_ndcg(hits, min(len(relevant), cutoff)))
        metrics["mrr"].append(next((1 / (index + 1) for index, hit in enumerate(key in relevant for key in keys) if hit), 0.0))
    return {
        "configuration": name,
        "questions": len(answerable),
        "recall@5": round(mean(metrics["recall@5"]), 4),
        "recall@10": round(mean(metrics["recall@10"]), 4),
        "mrr": round(mean(metrics["mrr"]), 4),
        "ndcg@5": round(mean(metrics["ndcg@5"]), 4),
        "ndcg@10": round(mean(metrics["ndcg@10"]), 4),
    }


def version_rate(documents: list[dict[str, object]], golden: list[dict[str, object]], retrieve: Callable[[str], list[tuple[dict[str, object], float]]]) -> float:
    cases = [row for row in golden if row.get("category") == "version_sensitive"]
    if not cases:
        return 0.0
    newest = 0
    for row in cases:
        top = retrieve(str(row["question"]))[:5]
        newest += int(bool(top) and not top[0][0].get("superseded_by"))
    return round(newest / len(cases), 4)


def tenant_probe(documents: list[dict[str, object]], embedder, use_hash: bool) -> dict[str, object]:
    bm25 = BM25Index(documents)
    dense = VectorIndex(documents)
    hybrid = HybridRetriever(bm25, dense, embedder)
    probes = ["payment aggregator requirements", "KYC requirements", "cyber security controls", "PPI limits", "e-mandate requirements"] * 4
    leaks = 0
    for tenant in ("A", "B"):
        for query in probes:
            results = hybrid.retrieve(query, filters=__import__("retrieval.interface", fromlist=["RetrievalFilters"]).RetrievalFilters(tenant=tenant))
            leaks += sum(document.get("tenant") != tenant for document, _ in results)
    return {"queries": 40, "per_tenant": 20, "cross_tenant_chunk_ids": leaks, "passed": leaks == 0}


def _ndcg(hits: list[bool], ideal_hits: int) -> float:
    dcg = sum((1.0 / __import__("math").log2(index + 2)) for index, hit in enumerate(hits) if hit)
    ideal = sum(1.0 / __import__("math").log2(index + 2) for index in range(ideal_hits))
    return dcg / ideal


def _effective_date(row: dict[str, str]) -> str | None:
    value = row.get("updated_as_on") or (row.get("page1_dates") or "").split(";")[0]
    for pattern in ("%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(value.strip(), pattern).date().isoformat()
        except ValueError:
            continue
    return None


def run(
    model_name: str = "BAAI/bge-small-en-v1.5",
    reranker_model: str = "BAAI/bge-reranker-base",
    use_hash: bool = False,
) -> list[dict[str, object]]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    golden = load_golden()
    all_results: list[dict[str, object]] = []
    reranker = CrossEncoderReranker(model_name=reranker_model)
    for child_words, overlap_words in ((200, 0), (200, 50), (400, 0), (400, 50), (800, 0), (800, 50)):
        documents, embedder = load_documents(child_words, overlap_words, model_name, use_hash)
        bm25 = BM25Index(documents)
        dense = VectorIndex(documents)
        hybrid = HybridRetriever(bm25, dense, embedder)
        retrievers = {
            "bm25": lambda query, index=bm25: index.search(query, 40),
            "dense": lambda query, index=dense, e=embedder: index.search(e.embed([query])[0], 40),
            "hybrid": lambda query, index=hybrid: index.retrieve(query, 40),
            "hybrid_reranker": lambda query, index=hybrid, r=reranker: r.rerank(query, index.retrieve(query, 40), 10),
        }
        for retriever_name, retrieve in retrievers.items():
            result = evaluate_configuration(
                f"{retriever_name}:{child_words}:{overlap_words}",
                documents,
                golden,
                retrieve,
            )
            result["version_citation_rate"] = version_rate(documents, golden, retrieve)
            all_results.append(result)
    payload = {"results": all_results, "tenant_probe": tenant_probe(documents, embedder, use_hash)}
    (RESULTS / "retrieval.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_markdown(all_results)
    return all_results


def _write_markdown(results: list[dict[str, object]]) -> None:
    lines = [
        "# Retrieval evaluation",
        "",
        "Relevance is exact chunk_id match from the golden set. "
        "Unanswerable and adversarial questions are excluded from retrieval metrics.",
        "",
        "| Configuration | Questions | Recall@5 | Recall@10 | MRR | nDCG@5 | nDCG@10 | Version citation rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        lines.append("| {configuration} | {questions} | {recall@5:.4f} | {recall@10:.4f} | {mrr:.4f} | {ndcg@5:.4f} | {ndcg@10:.4f} | {version_citation_rate:.4f} |".format(**result))
    (RESULTS / "retrieval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--reranker", default="BAAI/bge-reranker-base")
    parser.add_argument("--hash", action="store_true")
    args = parser.parse_args()
    output = run(args.model, args.reranker, args.hash)
    print(json.dumps(output, indent=2))
