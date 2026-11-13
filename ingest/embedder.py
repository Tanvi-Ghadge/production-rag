from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Iterable


class HashEmbedder:
    """Deterministic local embeddings with a content-hash cache."""

    def __init__(self, cache_path: Path, dimensions: int = 256) -> None:
        if dimensions < 16:
            raise ValueError("dimensions must be at least 16")
        self.cache_path = cache_path
        self.dimensions = dimensions
        self.model_name = "hash-v1"
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        loaded = json.loads(self.cache_path.read_text(encoding="utf-8")) if self.cache_path.exists() else {}
        self.cache = loaded.get("vectors", loaded) if isinstance(loaded, dict) else {}
        self.cache_hits = 0
        self.cache_misses = 0

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        vectors = [self._one(text) for text in texts]
        self.cache_path.write_text(json.dumps(self.cache, separators=(",", ":")), encoding="utf-8")
        return vectors

    def _one(self, text: str) -> list[float]:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if key in self.cache:
            self.cache_hits += 1
            return self.cache[key]
        self.cache_misses += 1
        vector = [0.0] * self.dimensions
        for token in re.findall(r"\w+", text.lower(), flags=re.UNICODE):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0 if digest[4] % 2 else -1.0
        norm = sum(value * value for value in vector) ** 0.5
        if norm:
            vector = [value / norm for value in vector]
        self.cache[key] = vector
        return vector


class SentenceTransformerEmbedder:
    """Batched Hugging Face sentence-transformers embeddings with model-aware cache."""

    def __init__(
        self,
        cache_path: Path,
        model_name: str = "BAAI/bge-small-en-v1.5",
        batch_size: int = 32,
        persist_cache: bool = True,
        lru_maxsize: int = 2048,
    ) -> None:
        from sentence_transformers import SentenceTransformer
        try:
            import torch
            threads = int(os.getenv("RAG_TORCH_THREADS", "4"))
            if threads > 0:
                torch.set_num_threads(threads)
        except Exception:
            pass

        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.model_name = model_name
        self.batch_size = batch_size
        self.cache_path = cache_path
        self.persist_cache = persist_cache
        self.lru_maxsize = lru_maxsize
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        loaded = json.loads(self.cache_path.read_text(encoding="utf-8")) if self.cache_path.exists() else {}
        raw_cache = loaded.get("vectors", loaded) if isinstance(loaded, dict) else {}
        self.cache: OrderedDict[str, list[float]] = OrderedDict(raw_cache)
        self.cache_hits = 0
        self.cache_misses = 0
        self.model = SentenceTransformer(model_name)
        self.dimensions = self.model.get_sentence_embedding_dimension()

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        values = list(texts)
        keys = [self._key(text) for text in values]
        vectors: list[list[float] | None] = []
        for key in keys:
            vec = self.cache.get(key)
            if vec is not None:
                self.cache.move_to_end(key)
            vectors.append(vec)
        missing_indices = [index for index, vector in enumerate(vectors) if vector is None]
        self.cache_hits += len(values) - len(missing_indices)
        self.cache_misses += len(missing_indices)
        if missing_indices:
            encoded = self.model.encode(
                [values[index] for index in missing_indices],
                batch_size=self.batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            for index, vector in zip(missing_indices, encoded):
                result = [float(value) for value in vector]
                self.cache[keys[index]] = result
                if not self.persist_cache and len(self.cache) > self.lru_maxsize:
                    self.cache.popitem(last=False)
                vectors[index] = result
        if missing_indices and self.persist_cache:
            self.cache_path.write_text(
                json.dumps(
                    {
                        "model_name": self.model_name,
                        "dimensions": self.dimensions,
                        "vectors": self.cache,
                    },
                    separators=(",", ":"),
                ),
                encoding="utf-8",
            )
        return [vector for vector in vectors if vector is not None]

    def _key(self, text: str) -> str:
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{self.model_name}:{content_hash}"