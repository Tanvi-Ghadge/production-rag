from __future__ import annotations

from collections import defaultdict
from statistics import median


class Metrics:
    def __init__(self) -> None:
        self.samples: dict[str, list[float]] = defaultdict(list)

    def observe(self, stage: str, milliseconds: float) -> None:
        self.samples[stage].append(milliseconds)

    def summary(self) -> dict[str, dict[str, float | int]]:
        return {
            stage: {
                "count": len(values),
                "p50_ms": round(median(values), 3),
                "p95_ms": round(sorted(values)[max(0, int(len(values) * 0.95) - 1)], 3),
            }
            for stage, values in self.samples.items()
        }