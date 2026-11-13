from __future__ import annotations

from threading import Lock
import time
from typing import Iterable
import re
import os

from ingest.embedder import HashEmbedder, SentenceTransformerEmbedder
from retrieval.interface import RetrievalFilters


class PgVectorRetriever:
    """PostgreSQL/pgvector dense retriever with tenant/date filtering."""

    def __init__(
        self,
        dsn: str,
        embedder: HashEmbedder | SentenceTransformerEmbedder,
        dimensions: int = 384,
        ef_search: int | None = None,
    ) -> None:
        self.dsn = dsn
        self.embedder = embedder
        self.dimensions = dimensions
        self.ef_search = ef_search or int(os.getenv("PGVECTOR_EF_SEARCH", "80"))
        self._conn = None
        self._lock = Lock()
        self.last_timings: dict[str, float] = {}

    def _get_connection(self):
        import psycopg

        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self.dsn)
        return self._conn

    def retrieve(
        self,
        query: str,
        top_k: int = 40,
        filters: RetrievalFilters | None = None,
    ) -> list[tuple[dict[str, object], float]]:
        original_query = query
        t0 = time.perf_counter()
        vector = self._vector_literal(self.embedder.embed([query])[0])
        t_embed = (time.perf_counter() - t0) * 1000.0

        clauses = ["1 = 1"]
        params: list[object] = [vector]
        if filters and filters.tenant is not None:
            clauses.append("tenant = %s")
            params.append(filters.tenant)
        if filters and filters.effective_after is not None:
            clauses.append("effective_date >= %s")
            params.append(filters.effective_after)
        if filters and filters.effective_before is not None:
            clauses.append("effective_date <= %s")
            params.append(filters.effective_before)
        candidate_limit = max(top_k, int(os.getenv("PGVECTOR_CANDIDATES", "100")))
        params.extend([vector, candidate_limit])
        sql = f"""
            SELECT chunk_id, parent_id, document_id, tenant, section_path, text,
                   page_start, page_end, content_hash, kind, effective_date,
                   1 - (embedding <=> %s::vector) AS score
            FROM chunks
            WHERE {' AND '.join(clauses)}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        t1 = time.perf_counter()
        with self._lock:
            for attempt in range(2):
                try:
                    conn = self._get_connection()
                    with conn.transaction():
                        with conn.cursor() as cursor:
                            cursor.execute(f"SET LOCAL hnsw.ef_search = {int(self.ef_search)}")
                            cursor.execute(sql, params)
                            rows = cursor.fetchall()
                    break
                except Exception:
                    if self._conn is not None:
                        try:
                            self._conn.close()
                        except Exception:
                            pass
                        self._conn = None
                    if attempt == 1:
                        raise
        t_pg = (time.perf_counter() - t1) * 1000.0

        t2 = time.perf_counter()
        fields = (
            "chunk_id", "parent_id", "document_id", "tenant", "section_path",
            "text", "page_start", "page_end", "content_hash", "kind", "effective_date",
        )
        candidates = [(dict(zip(fields, row[:-1])), float(row[-1])) for row in rows]
        query_terms = {
            term for term in re.findall(r"[a-z0-9]+", original_query.lower()) if len(term) > 2
        }
        ranked = []
        for document, dense_score in candidates:
            text_terms = set(re.findall(r"[a-z0-9]+", str(document["text"]).lower()))
            lexical = len(query_terms & text_terms) / max(len(query_terms), 1)
            ranked.append((document, dense_score * 0.7 + lexical * 0.3))
        result = sorted(ranked, key=lambda item: item[1], reverse=True)[:top_k]
        t_rescore = (time.perf_counter() - t2) * 1000.0
        self.last_timings = {
            "embed_ms": round(t_embed, 3),
            "pgvector_ms": round(t_pg, 3),
            "rescore_ms": round(t_rescore, 3),
        }
        return result

    @staticmethod
    def _vector_literal(vector: Iterable[float]) -> str:
        return "[" + ",".join(str(float(value)) for value in vector) + "]"
