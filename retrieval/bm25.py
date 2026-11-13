from __future__ import annotations

import math
import re
from collections import Counter

from retrieval.interface import RetrievalFilters, matches_filters


class BM25Index:
    def __init__(self, documents: list[dict[str, object]] | None = None, k1: float = 1.5, b: float = 0.75) -> None:
        self.documents = documents or []
        self.k1 = k1
        self.b = b
        self._build()

    def _build(self) -> None:
        self.term_frequency = []
        self.document_frequency: Counter[str] = Counter()
        lengths = []
        for document in self.documents:
            searchable = f"{document.get('document_id', '')} {document.get('section_path', '')} {document.get('text', '')}"
            counts = Counter(_tokens(searchable))
            self.term_frequency.append(counts)
            self.document_frequency.update(counts.keys())
            lengths.append(sum(counts.values()))
        self.average_length = sum(lengths) / len(lengths) if lengths else 0.0

    def search(
        self,
        query: str,
        top_k: int = 40,
        filters: RetrievalFilters | None = None,
    ) -> list[tuple[dict[str, object], float]]:
        query_terms = _tokens(query)
        n = len(self.documents)
        scored = []
        for index, document in enumerate(self.documents):
            if not matches_filters(document, filters):
                continue
            length = sum(self.term_frequency[index].values())
            score = 0.0
            for term in query_terms:
                frequency = self.term_frequency[index][term]
                if not frequency:
                    continue
                idf = math.log(1 + (n - self.document_frequency[term] + 0.5) /
                               (self.document_frequency[term] + 0.5))
                denominator = frequency + self.k1 * (1 - self.b + self.b * length / (self.average_length or 1))
                score += idf * frequency * (self.k1 + 1) / denominator
            if score:
                scored.append((document, score))
        return sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)