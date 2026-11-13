from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    requests = None
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda *args, **kwargs: None

from evals.judge import judge, summarize


_SSE = re.compile(r"event: final\s*\ndata: (\{.*?\})\n\ndata: \[DONE\]", re.DOTALL)
EVAL_VERSION = "grounded-context-v8-rerank-stage-trace"


def _records(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("//")
    ][:limit]


def _answer_payload(response: requests.Response) -> dict[str, Any]:
    if response.status_code == 422:
        try:
            detail = response.json().get("detail", "")
        except ValueError:
            detail = ""
        if "prompt injection" in str(detail).lower() or "outside" in str(detail).lower():
            return {
                "trace_id": None,
                "query": "",
                "trace": {},
                "answer": "I cannot answer this because it is outside the regulatory corpus.",
                "refused": True,
                "citations": [],
                "guarded_refusal": True,
            }
    match = _SSE.search(response.text)
    if not match:
        raise ValueError("API response is not a complete SSE answer")
    payload = json.loads(match.group(1))
    required = {"trace_id", "query", "trace", "answer", "refused", "citations"}
    if not required <= payload.keys():
        raise ValueError("API answer schema is invalid")
    if not isinstance(payload["answer"], str) or not isinstance(payload["refused"], bool):
        raise ValueError("API answer types are invalid")
    if not isinstance(payload["citations"], list):
        raise ValueError("API citations are invalid")
    return payload


def _index_records(root: Path) -> dict[str, dict[str, Any]]:
    index = root / "data" / "index" / "chunks.jsonl"
    return {
        str(item["chunk_id"]): item
        for item in (json.loads(line) for line in index.read_text(encoding="utf-8").splitlines())
    }


def _score_result(
    payload: dict[str, Any],
    record: dict[str, Any],
    indexed: dict[str, dict[str, Any]],
) -> dict[str, object]:
    tenant = str(record["source_passages"][0].get("tenant"))
    expected_refusal = not bool(record["answerable"])
    citations = payload["citations"]

    if payload["refused"] and expected_refusal:
        return {
            "refusal_correct": True,
            "citation_correct": not citations,
            "faithfulness": 1.0,
            "correctness": 1.0,
            "failure": "none",
            "judge": "policy_refusal",
        }

    cited_records = [
        indexed[str(item["chunk_id"])]
        for item in citations
        if str(item.get("chunk_id")) in indexed
    ]
    citation_ids = {str(item.get("chunk_id")) for item in citations}
    expected_docs = {str(item["document_id"]) for item in record["source_passages"]}
    expected_pages = {int(item["page"]) for item in record["source_passages"]}
    citation_correct = (
        (payload["refused"] and not citations)
        or (
            not payload["refused"]
            and bool(cited_records)
            and all(str(item.get("tenant")) == tenant for item in citations)
            and any(
                str(item["document_id"]) in expected_docs
                and int(item["page_start"]) in expected_pages
                for item in cited_records
            )
        )
    )
    context = " ".join(str(item.get("text", "")) for item in cited_records)
    scores = judge(str(payload["answer"]), str(record["reference_answer"]), context)
    return {
        "refusal_correct": payload["refused"] is expected_refusal,
        "citation_correct": citation_correct,
        **scores,
    }


def run_api(
    golden: Path,
    output: Path,
    *,
    base_url: str,
    api_key: str,
    timeout: float = 120,
) -> dict[str, object]:
    root = golden.parents[2]
    indexed = _index_records(root)
    existing: dict[str, dict[str, object]] = {}
    if output.exists():
        try:
            previous = json.loads(output.read_text(encoding="utf-8"))
            if previous.get("evaluation_version") == EVAL_VERSION:
                existing = {str(item["id"]): item for item in previous.get("results", [])}
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            existing = {}
    results: list[dict[str, object]] = []
    session = requests.Session()
    for record in _records(golden):
        if record["id"] in existing and existing[record["id"]].get("schema_valid") is True:
            cached = existing[record["id"]]
            cached.update(_score_result(
                {"answer": cached["answer"], "refused": cached["refused"], "citations": cached["citations"]},
                record,
                indexed,
            ))
            results.append(cached)
            print(f"{len(results)} {record['id']} cached", flush=True)
            continue
        tenant = record["source_passages"][0].get("tenant")
        started = time.perf_counter()
        response = session.post(
            f"{base_url.rstrip('/')}/v1/ask",
            headers={"X-API-Key": api_key},
            json={"question": record["question"], "tenant": tenant},
            timeout=timeout,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        try:
            payload = _answer_payload(response)
        except ValueError as exc:
            results.append({
                "id": record["id"],
                "status_code": response.status_code,
                "latency_ms": elapsed_ms,
                "trace_id": None,
                "schema_valid": False,
                "refusal_correct": False,
                "citation_correct": False,
                "answer": "",
                "refused": False,
                "citations": [],
                "faithfulness": 0.0,
                "correctness": 0.0,
                "failure": f"schema_error: {exc}",
                "body_prefix": response.text[:500],
            })
            partial = summarize(results)
            partial["evaluation_version"] = EVAL_VERSION
            partial["results"] = results
            output.write_text(json.dumps(partial, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"{len(results)} {record['id']} schema error", flush=True)
            continue
        scores = _score_result(payload, record, indexed)
        results.append({
            "id": record["id"],
            "status_code": response.status_code,
            "latency_ms": elapsed_ms,
            "trace_id": payload["trace_id"],
            "schema_valid": True,
            **scores,
            "answer": payload["answer"],
            "refused": payload["refused"],
            "citations": payload["citations"],
        })
        partial = summarize(results)
        partial["results"] = results
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(partial, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{len(results)} {record['id']} complete", flush=True)
    summary = summarize(results)
    summary.update({
        "evaluation_version": EVAL_VERSION,
        "schema_valid": all(bool(item["schema_valid"]) for item in results),
        "refusal_accuracy": round(
            sum(bool(item["refusal_correct"]) for item in results) / len(results), 4
        ),
        "citation_accuracy": round(
            sum(bool(item["citation_correct"]) for item in results) / len(results), 4
        ),
        "results": results,
    })
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def run(*args: Any, **kwargs: Any) -> dict[str, object]:
    return run_api(*args, **kwargs)


if __name__ == "__main__":
    root = Path(__file__).parents[1]
    load_dotenv(root / ".env", override=True)
    key = os.getenv("RAG_API_KEYS", "").split(",")[0].strip()
    if not key:
        raise SystemExit("RAG_API_KEYS is required to evaluate the API")
    print(run_api(
        root / "evals/golden/golden.jsonl",
        root / "evals/results/answers.json",
        base_url=os.getenv("RAG_EVAL_API_URL", "http://127.0.0.1:8000"),
        api_key=key,
    ))
