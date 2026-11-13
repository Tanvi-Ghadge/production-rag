"""Steady-state latency and TTFT benchmark (Track A6).

Discards warm-up requests, runs 200+ queries against FastAPI TestClient
with lifespan enabled, measures per-stage latency and SSE time-to-first-token,
and reports cold-start separately from steady-state p50/p95.
"""

from __future__ import annotations

import json
import os
import re
from math import ceil
from pathlib import Path
from statistics import median
from time import perf_counter

from dotenv import load_dotenv

ROOT = Path(__file__).parents[1]
load_dotenv(ROOT / ".env", override=True)
os.environ["RAG_ASK_RATE_LIMIT"] = "10000"

from fastapi.testclient import TestClient
from app.main import app


def _percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, ceil(len(ordered) * p) - 1))
    return round(ordered[idx], 3)


def _load_sample_questions(limit: int = 25) -> list[dict[str, str]]:
    golden_path = ROOT / "evals" / "golden" / "golden.jsonl"
    items = []
    for line in golden_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not row.get("answerable", False):
            continue
        passages = row.get("source_passages") or []
        tenant = passages[0].get("tenant", "A") if passages else "A"
        items.append({"question": str(row["question"]), "tenant": str(tenant)})
        if len(items) >= limit:
            break
    return items


def run_benchmark(warmup: int = 10, total_queries: int = 200) -> dict[str, object]:
    questions = _load_sample_questions(limit=25)
    t_boot = perf_counter()
    with TestClient(app) as client:
        boot_ms = round((perf_counter() - t_boot) * 1000.0, 3)
        health = client.get("/v1/health").json()
        cold_start_ms = float(health.get("cold_start_ms", boot_ms))

        # Warm-up (discarded)
        for i in range(warmup):
            q = questions[i % len(questions)]
            client.post("/v1/ask", headers={"X-API-Key": "dev-key"}, json=q)

        stages: dict[str, list[float]] = {}
        totals: list[float] = []
        ttfts: list[float] = []
        cache_hits = 0

        for i in range(total_queries):
            q = questions[i % len(questions)]
            t0 = perf_counter()
            ttft_ms: float | None = None
            final_payload: dict[str, object] | None = None
            with client.stream(
                "POST",
                "/v1/ask",
                headers={"X-API-Key": "dev-key"},
                json=q,
            ) as resp:
                for line in resp.iter_lines():
                    if not line:
                        continue
                    if ttft_ms is None and line.startswith("data:") and '"token"' in line:
                        ttft_ms = (perf_counter() - t0) * 1000.0
                    if line.startswith("data:") and '"trace_id"' in line:
                        final_payload = json.loads(line[len("data:"):].strip())
            total_ms = (perf_counter() - t0) * 1000.0
            totals.append(total_ms)
            ttfts.append(ttft_ms if ttft_ms is not None else total_ms)

            if final_payload:
                if final_payload.get("cache_hit"):
                    cache_hits += 1
                for stage, vals in (final_payload.get("trace") or {}).items():
                    if isinstance(vals, dict) and "latency_ms" in vals:
                        stages.setdefault(stage, []).append(float(vals["latency_ms"]))

    report = {
        "warmup_discarded": warmup,
        "steady_state_queries": total_queries,
        "cold_start_ms": round(cold_start_ms, 3),
        "cache_hit_rate": round(cache_hits / max(1, total_queries), 4),
        "note_cache_warm": "p50/p95 numbers include 92.5% cache-hit requests; cold-miss p95 shown in generate.p95",
        "ttft_ms": {
            "p50_ms": round(median(ttfts), 3),
            "p95_ms": _percentile(ttfts, 0.95),
        },
        "total_ms": {
            "p50_ms": round(median(totals), 3),
            "p95_ms": _percentile(totals, 0.95),
        },
        "stages": {
            stage: {
                "count": len(vals),
                "p50_ms": round(median(vals), 3),
                "p95_ms": _percentile(vals, 0.95),
            }
            for stage, vals in stages.items()
            if vals
        },
    }
    # Phase 0f: account for the gap between stage sum and wall-clock total
    stage_sum_p50 = sum(
        s["p50_ms"] for s in report["stages"].values()
    )
    report["stage_sum_p50_ms"] = round(stage_sum_p50, 3)
    report["unaccounted_overhead_p50_ms"] = round(report["total_ms"]["p50_ms"] - stage_sum_p50, 3)
    report["overhead_note"] = (
        "Overhead = ASGI request parsing + SSE StreamingResponse flush + "
        "TestClient HTTP framing. Stage timings are measured inside the route handler; "
        "ASGI middleware and network round-trip are outside the trace."
    )
    out_path = ROOT / "evals" / "results" / "latency-after.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run_benchmark(), indent=2))
