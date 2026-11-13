from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from ingest.chunker import structure_aware_chunks
from ingest.embedder import HashEmbedder
from ingest.embedder import SentenceTransformerEmbedder
from ingest.indexer import LocalIndex
from ingest.parsers.pdf import parse_pdf


_VERSION_RELATIONSHIPS = {
    "pa_guidelines_2020.pdf": (None, "pa_md_2025.pdf"),
    "pa_circular_2021.pdf": (None, "pa_md_2025.pdf"),
    "pa_md_2025.pdf": ("pa_guidelines_2020.pdf", None),
    "kyc_md_2016.pdf": (None, "kyc_md_2025.pdf"),
    "kyc_md_2025.pdf": ("kyc_md_2016.pdf", None),
    "cyber_md_2024.pdf": (None, "cyber_md_2026.pdf"),
    "cyber_md_2026.pdf": ("cyber_md_2024.pdf", None),
    "ppi_md_2017.pdf": (None, "ppi_md_2021.pdf"),
    "ppi_md_2021.pdf": ("ppi_md_2017.pdf", None),
    "emandate_2022.pdf": (None, "emandate_2023.pdf"),
    "emandate_2023.pdf": ("emandate_2022.pdf", "emandate_2024.pdf"),
    "emandate_2024.pdf": ("emandate_2023.pdf", "emandate_framework_2026.pdf"),
    "emandate_framework_2026.pdf": ("emandate_2024.pdf", None),
}


def run(
    corpus_dir: Path,
    audit_path: Path,
    index_dir: Path,
    model_name: str = "BAAI/bge-small-en-v1.5",
    use_hash: bool = False,
) -> dict[str, object]:
    with audit_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    index = LocalIndex(index_dir)
    embedder = (
        HashEmbedder(index_dir / "embedding-cache.json")
        if use_hash
        else SentenceTransformerEmbedder(index_dir / "embedding-cache.json", model_name)
    )
    total_chunks = 0
    changed_chunks = 0
    documents = 0
    jobs = []
    for row in rows:
        path = corpus_dir / row["tenant"] / row["file"]
        if not path.exists():
            raise FileNotFoundError(path)
        parsed = parse_pdf(path)
        if not parsed.text:
            jobs.append({"file": row["file"], "status": "needs_ocr", "chunks": 0})
            continue
        chunks = structure_aware_chunks(
            parsed,
            f"{row['tenant']}:{path.stem}",
            row["tenant"],
            effective_date=_effective_date(row),
            supersedes=_VERSION_RELATIONSHIPS.get(row["file"], (None, None))[0],
            superseded_by=_VERSION_RELATIONSHIPS.get(row["file"], (None, None))[1],
        )
        changed, total = index.upsert(chunks, embedder)
        total_chunks = total
        changed_chunks += changed
        documents += 1
        jobs.append({"file": row["file"], "status": "completed", "chunks": len(chunks), "changed_chunks": changed})
    state = {
        "release": "corpus-2026-11-09",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "documents": documents,
        "total_chunks": total_chunks,
        "changed_chunks": changed_chunks,
        "embedding_cache_hits": embedder.cache_hits,
        "embedding_cache_misses": embedder.cache_misses,
        "embedding_model": getattr(embedder, "model_name", "hash"),
        "embedding_dimensions": getattr(embedder, "dimensions", 256),
        "idempotency": {
            "new_chunk_ids": changed_chunks,
            "embedding_cache_misses": embedder.cache_misses,
        },
        "jobs": jobs,
    }
    index.save_state(state)
    return state


def _effective_date(row: dict[str, str]) -> str | None:
    value = row.get("updated_as_on") or (row.get("page1_dates") or "").split(";")[0]
    match = re.search(r"(\w+ \d{1,2}, \d{4}|\d{1,2} \w+ \d{4})", value)
    if not match:
        return None
    from datetime import datetime

    for pattern in ("%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(match.group(1), pattern).date().isoformat()
        except ValueError:
            continue
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("corpus/raw"))
    parser.add_argument("--audit", type=Path, default=Path("corpus/audit.csv"))
    parser.add_argument("--index", type=Path, default=Path("data/index"))
    parser.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--hash-embeddings", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.corpus, args.audit, args.index, args.model, args.hash_embeddings), indent=2))


if __name__ == "__main__":
    main()
