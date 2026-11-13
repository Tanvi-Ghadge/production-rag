from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
import random
import time
from typing import Protocol


class Provider(Protocol):
    def __call__(self, prompt: str) -> tuple[str, int, int]:
        ...


@dataclass
class Circuit:
    failures: int = 0
    opened_at: float = 0.0


class LLMClient:
    def __init__(
        self, providers: list[Provider], *, timeout: float = 30,
        retries: int = 2, cache: object | None = None,
        cost_per_1k_tokens: float = 0.0,
    ) -> None:
        if not providers:
            raise ValueError("at least one provider is required")
        self.providers = providers
        self.timeout = timeout
        self.retries = retries
        self.cache = cache
        self.cost_per_1k_tokens = cost_per_1k_tokens
        self.circuits = [Circuit() for _ in providers]
        self.cost_log: list[dict[str, float | int]] = []
        self.cache_hit = False

    def complete(self, prompt: str) -> str:
        last_error: Exception | None = None
        if self.cache is not None:
            cached = self.cache.get(prompt)
            if cached is not None:
                self.cache_hit = True
                return str(cached)
        self.cache_hit = False
        for index, provider in enumerate(self.providers):
            circuit = self.circuits[index]
            if circuit.failures >= 3 and time.monotonic() - circuit.opened_at < 30:
                continue
            for attempt in range(self.retries + 1):
                try:
                    started = time.monotonic()
                    pool = ThreadPoolExecutor(max_workers=1)
                    future = pool.submit(provider, prompt)
                    try:
                        result, prompt_tokens, completion_tokens = future.result(self.timeout)
                    except FutureTimeout as exc:
                        future.cancel()
                        raise TimeoutError("LLM provider timeout") from exc
                    finally:
                        pool.shutdown(wait=False, cancel_futures=True)
                    circuit.failures = 0
                    tokens = prompt_tokens + completion_tokens
                    self.cost_log.append({"tokens": tokens, "cost": tokens / 1000 * self.cost_per_1k_tokens})
                    if self.cache is not None:
                        self.cache.set(prompt, result)
                    return result
                except Exception as exc:
                    last_error = exc
                    circuit.failures += 1
                    circuit.opened_at = time.monotonic()
                    if attempt < self.retries:
                        time.sleep((2**attempt) * 0.05 + random.random() * 0.05)
        raise RuntimeError(f"all LLM providers failed: {last_error}") from last_error