from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from uuid import uuid4


@dataclass
class Trace:
    trace_id: str = field(default_factory=lambda: uuid4().hex)
    stages: dict[str, dict[str, float | int]] = field(default_factory=dict)

    def stage(self, name: str) -> "_Stage":
        return _Stage(self, name)

    def record(self, name: str, started: float, tokens: int = 0, cost: float = 0.0) -> None:
        self.stages[name] = {
            "latency_ms": round((perf_counter() - started) * 1000, 3),
            "tokens": tokens,
            "cost": cost,
        }


class _Stage:
    def __init__(self, trace: Trace, name: str) -> None:
        self.trace, self.name, self.started = trace, name, perf_counter()

    def __enter__(self) -> "_Stage":
        return self

    def __exit__(self, *_: object) -> None:
        self.trace.record(self.name, self.started)