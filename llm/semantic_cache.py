from __future__ import annotations

import hashlib
import math
import re
import time


class SemanticCache:
    """Optional in-memory embedding-similarity cache."""

    def __init__(self, similarity: float = 0.92, ttl: int = 3600, embed=None) -> None:
        self.similarity = similarity
        self.ttl = ttl
        self.embed = embed or self._embed
        self._entries: list[tuple[list[float], str, float]] = []
        self.last_hit = False

    @staticmethod
    def _embed(value: str) -> list[float]:
        """Stable signed hashing embedding; callers may provide a real model."""
        vector = [0.0] * 128
        for term in re.findall(r"[a-z0-9]+", value.lower()):
            digest = hashlib.sha256(term.encode()).digest()
            vector[digest[0] % len(vector)] += -1.0 if digest[1] & 1 else 1.0
        norm = math.sqrt(sum(item * item for item in vector)) or 1.0
        return [item / norm for item in vector]

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        return sum(a * b for a, b in zip(left, right))

    def get(self, value: str) -> str | None:
        now = time.monotonic()
        self._entries = [entry for entry in self._entries if now - entry[2] < self.ttl]
        vector = self.embed(value)
        best = max(
            self._entries,
            key=lambda entry: self._cosine(vector, entry[0]),
            default=None,
        )
        if best is None:
            self.last_hit = False
            return None
        score = self._cosine(vector, best[0])
        self.last_hit = score >= self.similarity
        return best[1] if self.last_hit else None

    def set(self, value: str, result: str, ttl: int | None = None) -> None:
        self._entries.append((self.embed(value), result, time.monotonic()))
