from __future__ import annotations

import json
from pathlib import Path

from ingest.chunker import Chunk
from ingest.embedder import HashEmbedder, SentenceTransformerEmbedder
from retrieval.bm25 import BM25Index
from retrieval.dense import VectorIndex
from retrieval.hybrid import HybridRetriever


class LocalIndex:
    def __init__(self, index_dir: Path) -> None:
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_path = index_dir / "chunks.jsonl"
        self.state_path = index_dir / "state.json"

    def load_chunks(self) -> list[dict[str, object]]:
        if not self.chunks_path.exists():
            return []
        return [json.loads(line) for line in self.chunks_path.read_text(encoding="utf-8").splitlines()]

    def upsert(self, chunks: list[Chunk], embedder: HashEmbedder | SentenceTransformerEmbedder) -> tuple[int, int]:
        existing = {str(item["chunk_id"]): item for item in self.load_chunks()}
        changed = [
            chunk for chunk in chunks
            if existing.get(chunk.chunk_id, {}).get("content_hash") != chunk.content_hash
            or "effective_date" not in existing.get(chunk.chunk_id, {})
            or existing.get(chunk.chunk_id, {}).get("effective_date") != chunk.effective_date
            or existing.get(chunk.chunk_id, {}).get("supersedes") != chunk.supersedes
            or existing.get(chunk.chunk_id, {}).get("superseded_by") != chunk.superseded_by
            or existing.get(chunk.chunk_id, {}).get("embedding_model") != embedder.model_name
        ]
        vectors = embedder.embed(chunk.text for chunk in changed)
        for chunk, vector in zip(changed, vectors):
            item = chunk.to_dict()
            item["embedding"] = vector
            item["embedding_model"] = embedder.model_name
            existing[chunk.chunk_id] = item
        ordered = [existing[key] for key in sorted(existing)]
        self.chunks_path.write_text(
            "\n".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in ordered) +
            ("\n" if ordered else ""),
            encoding="utf-8",
        )
        return len(changed), len(existing)

    def save_state(self, state: dict[str, object]) -> None:
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def bm25(self) -> BM25Index:
        return BM25Index(self.load_chunks())

    def vector(self) -> VectorIndex:
        return VectorIndex(self.load_chunks())

    def hybrid(self, embedder: HashEmbedder | SentenceTransformerEmbedder) -> HybridRetriever:
        chunks = self.load_chunks()
        return HybridRetriever(BM25Index(chunks), VectorIndex(chunks), embedder)
