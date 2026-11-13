from __future__ import annotations

from typing import Iterable


class PgVectorIndex:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def upsert(self, records: Iterable[dict[str, object]]) -> int:
        import psycopg

        rows = list(records)
        if not rows:
            return 0
        query = """
            INSERT INTO chunks (
                chunk_id, parent_id, document_id, tenant, section_path, text,
                page_start, page_end, content_hash, kind, effective_date,
                embedding, embedding_model
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s
            )
            ON CONFLICT (chunk_id) DO UPDATE SET
                parent_id = EXCLUDED.parent_id,
                document_id = EXCLUDED.document_id,
                tenant = EXCLUDED.tenant,
                section_path = EXCLUDED.section_path,
                text = EXCLUDED.text,
                page_start = EXCLUDED.page_start,
                page_end = EXCLUDED.page_end,
                content_hash = EXCLUDED.content_hash,
                kind = EXCLUDED.kind,
                effective_date = EXCLUDED.effective_date,
                embedding = EXCLUDED.embedding,
                embedding_model = EXCLUDED.embedding_model
        """
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.executemany(query, [_params(row) for row in rows])
            connection.commit()
        return len(rows)


def _params(row: dict[str, object]) -> tuple[object, ...]:
    vector = "[" + ",".join(str(float(value)) for value in row["embedding"]) + "]"
    return (
        row["chunk_id"], row["parent_id"], row["document_id"], row["tenant"],
        row["section_path"], row["text"], row["page_start"], row["page_end"],
        row["content_hash"], row["kind"], row["effective_date"], vector,
        row["embedding_model"],
    )
