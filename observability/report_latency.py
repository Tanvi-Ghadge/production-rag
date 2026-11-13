from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from math import ceil


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, ceil(len(ordered) * percentile_value) - 1))
    return round(ordered[index], 3)


def build(input_path: Path, output_path: Path) -> dict[str, object]:
    evidence = json.loads(input_path.read_text(encoding="utf-8"))
    samples: dict[str, list[float]] = {}
    cache_samples: dict[str, list[float]] = {"hit": [], "miss": []}
    queries = list(evidence.get("queries", []))
    repeat = evidence.get("cache_repeat", {})
    queries.extend(
        item for item in (repeat.get("first"), repeat.get("second")) if isinstance(item, dict)
    )
    for query in queries:
        samples.setdefault("total", []).append(float(query["latency_ms"]))
        cache_samples["hit" if query.get("cache_hit") else "miss"].append(float(query["latency_ms"]))
        for stage, values in (query.get("trace") or {}).items():
            samples.setdefault(stage, []).append(float(values["latency_ms"]))
    report: dict[str, object] = {
        "source": str(input_path),
        "note": "Descriptive metrics from captured successful traces; not a controlled benchmark.",
        "stages": {
            stage: {
                "count": len(values),
                "p50_ms": round(median(values), 3),
                "p95_ms": percentile(values, 0.95),
            }
            for stage, values in samples.items()
            if values
        },
    }
    report["cache_latency"] = {
        state: {
            "count": len(values),
            "p50_ms": round(median(values), 3),
            "p95_ms": percentile(values, 0.95),
        }
        for state, values in cache_samples.items()
        if values
    }
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    root = Path(__file__).parents[1]
    print(build(
        root / "evals/results/runtime-evidence.json",
        root / "evals/results/latency.json",
    ))
