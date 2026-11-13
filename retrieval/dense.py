from __future__ import annotations

import math

import numpy as np

from retrieval.interface import RetrievalFilters, matches_filters


class VectorIndex:
    def __init__(self, documents: list[dict[str, object]] | None = None) -> None:
        self.documents = documents or []
        self._matrix = np.asarray(
            [document["embedding"] for document in self.documents],
            dtype=np.float32,
        )
        self._norms = np.linalg.norm(self._matrix, axis=1) if self.documents else np.array([])

    def search(
        self,
        query_vector: list[float],
        top_k: int = 40,
        filters: RetrievalFilters | None = None,
    ) -> list[tuple[dict[str, object], float]]:
        if not self.documents:
            return []
        query = np.asarray(query_vector, dtype=np.float32)
        query_norm = np.linalg.norm(query)
        scores = self._matrix @ query / (self._norms * query_norm + 1e-12)
        scored = [
            (document, float(score))
            for document, score in zip(self.documents, scores)
            if matches_filters(document, filters)
        ]
        return sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]


def _cosine(left: list[float], right: object) -> float:
    vector = [float(value) for value in right]  # type: ignore[arg-type]
    denominator = math.sqrt(sum(x * x for x in left) * sum(y * y for y in vector))
    return sum(x * y for x, y in zip(left, vector)) / denominator if denominator else 0.0