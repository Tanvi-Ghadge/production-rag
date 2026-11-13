from __future__ import annotations

import re
from typing import Callable, Iterable


class CrossEncoderReranker:
    """Rerank candidates with an injected scorer or sentence-transformers."""

    def __init__(
        self,
        scorer: Callable[[list[tuple[str, str]]], Iterable[float]] | None = None,
        model_name: str | None = None,
    ) -> None:
        if scorer is not None and model_name is not None:
            raise ValueError("provide scorer or model_name, not both")
        if model_name is not None:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder(model_name)
            self.scorer = lambda pairs: model.predict(pairs)
        else:
            self.scorer = scorer

    def rerank(
        self,
        query: str,
        candidates: list[tuple[dict[str, object], float]],
        top_k: int = 8,
    ) -> list[tuple[dict[str, object], float]]:
        if not candidates:
            return []
        pairs = [(query, str(document["text"])) for document, _ in candidates]
        scores = (
            list(self.scorer(pairs))
            if self.scorer is not None
            else [_lexical_score(query, text) for _, text in pairs]
        )
        if len(scores) != len(candidates):
            raise ValueError("reranker scorer returned the wrong number of scores")
        ranked = [
            (document, float(score))
            for (document, _), score in zip(candidates, scores)
        ]
        return sorted(ranked, key=lambda item: item[1], reverse=True)[:top_k]


def _lexical_score(query: str, text: str) -> float:
    query_terms = set(re.findall(r"\w+", query.lower()))
    text_terms = re.findall(r"\w+", text.lower())
    return sum(text_terms.count(term) for term in query_terms) / max(len(text_terms), 1)