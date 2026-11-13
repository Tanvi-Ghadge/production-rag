from __future__ import annotations

import re

from ingest.embedder import HashEmbedder, SentenceTransformerEmbedder
from retrieval.bm25 import BM25Index
from retrieval.dense import VectorIndex
from retrieval.interface import RetrievalFilters

_IDENTIFIER_RE = re.compile(
    r"(?:Section\s+\d+(?:\(\d+\))?|Rule\s+\d+(?:\(\d+\))?|Form\s+[A-Z0-9]+|"
    r"Paragraph\s+\d+(?:\.\d+)*|RBI/\d{4}-\d{2}/[A-Za-z0-9.-]+|"
    r"DPSS\.[A-Z0-9./-]+|CO\.DPSS\.[A-Z0-9./-]+|\b(?:A|B):[a-z0-9_.-]+)",
    re.IGNORECASE,
)


def extract_identifiers(query: str) -> list[str]:
    return [m.group(0).strip() for m in _IDENTIFIER_RE.finditer(query)]


class HybridRetriever:
    def __init__(
        self,
        bm25: BM25Index,
        dense: VectorIndex,
        embedder: HashEmbedder | SentenceTransformerEmbedder,
        fusion_k: int = 60,
        bm25_weight: float = 1.0,
        dense_weight: float = 1.0,
        freshness_boost: float = 0.002,
        identifier_boost: float = 0.015,
    ) -> None:
        self.bm25 = bm25
        self.dense = dense
        self.embedder = embedder
        self.fusion_k = fusion_k
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight
        self.freshness_boost = freshness_boost
        self.identifier_boost = identifier_boost

    def retrieve(
        self,
        query: str,
        top_k: int = 40,
        filters: RetrievalFilters | None = None,
    ) -> list[tuple[dict[str, object], float]]:
        lexical = self.bm25.search(query, top_k, filters)
        vector = self.dense.search(self.embedder.embed([query])[0], top_k, filters)
        by_id: dict[str, tuple[dict[str, object], float]] = {}
        for rank, (document, _) in enumerate(lexical, start=1):
            by_id[str(document["chunk_id"])] = (document, self.bm25_weight / (self.fusion_k + rank))
        for rank, (document, _) in enumerate(vector, start=1):
            chunk_id = str(document["chunk_id"])
            score = self.dense_weight / (self.fusion_k + rank)
            existing = by_id.get(chunk_id)
            by_id[chunk_id] = (document, score + (existing[1] if existing else 0.0))

        identifiers = [ident.lower() for ident in extract_identifiers(query)]
        boosted = []
        for document, score in by_id.values():
            extra = self.freshness_boost if not document.get("superseded_by") else 0.0
            if identifiers and self.identifier_boost > 0:
                haystack = f"{document.get('document_id', '')} {document.get('section_path', '')} {document.get('text', '')}".lower()
                if any(ident in haystack for ident in identifiers):
                    extra += self.identifier_boost
            boosted.append((document, score + extra))
        return sorted(boosted, key=lambda item: item[1], reverse=True)[:top_k]
