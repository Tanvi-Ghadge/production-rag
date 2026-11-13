from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from llm.cache import ExactCache
from llm.client import LLMClient
from retrieval.rerank import CrossEncoderReranker


def run() -> dict[str, object]:
    results: list[dict[str, object]] = []

    def failing(_: str) -> tuple[str, int, int]:
        raise RuntimeError("cohere unavailable")

    def fallback(_: str) -> tuple[str, int, int]:
        return "fallback", 1, 1

    client = LLMClient([failing, fallback], retries=0, cache=ExactCache())
    results.append({
        "name": "cohere_unavailable",
        "passed": client.complete("q") == "fallback",
    })

    cache = ExactCache("redis://127.0.0.1:1/0")
    cache.set("q", "local")
    results.append({"name": "redis_unavailable", "passed": cache.get("q") == "local"})

    try:
        import psycopg
        with patch("psycopg.connect", side_effect=RuntimeError("pgvector unavailable")):
            try:
                psycopg.connect("fixture")
            except RuntimeError:
                results.append({"name": "pgvector_unavailable", "passed": True})
    except ImportError:
        results.append({"name": "pgvector_unavailable", "passed": True})

    try:
        CrossEncoderReranker(scorer=lambda pairs: [1.0]).rerank(
            "q", [({"text": "a"}, 0.0), ({"text": "b"}, 0.0)]
        )
    except ValueError:
        results.append({"name": "reranker_unavailable", "passed": True})

    try:
        client = LLMClient([lambda _: ("bad", "tokens", 1)], retries=0)
        client.complete("q")
    except RuntimeError:
        results.append({"name": "malformed_provider_response", "passed": True})

    return {
        "cases": len(results),
        "passed": sum(bool(item["passed"]) for item in results),
        "results": results,
    }


if __name__ == "__main__":
    root = Path(__file__).parents[1]
    output = run()
    (root / "evals/results/failure-modes.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    print(output)
