from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[2]
GOLDEN = Path(__file__).with_name("golden.jsonl")
INDEX = ROOT / "data" / "index" / "chunks.jsonl"
REQUIRED = {"id", "category", "question", "answerable", "reference_answer", "source_passages"}
ALLOWED = {"factoid", "multi_hop", "table_lookup", "version_sensitive", "unanswerable", "adversarial"}


def validate() -> list[dict[str, object]]:
    records = [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines()]
    indexed = {
        record["chunk_id"]: record
        for record in (json.loads(line) for line in INDEX.read_text(encoding="utf-8").splitlines())
    }
    assert 100 <= len(records) <= 150, len(records)
    assert len({record["id"] for record in records}) == len(records)
    for record in records:
        assert REQUIRED <= record.keys()
        assert record["review_status"] in {"needs_human_review", "reviewed", "human-reviewed"}
        assert record["category"] in ALLOWED
        assert record["question"].strip()
        assert record["source_passages"]
        assert all(passage["chunk_id"] in indexed for passage in record["source_passages"])
        if record["category"] == "adversarial":
            assert record["adversarial"] is True
            assert record["answerable"] is False
        if record["category"] == "version_sensitive":
            assert len({passage["document_id"] for passage in record["source_passages"]}) == 2
            assert len(record["supersession_pair"]) == 2
        if not record["answerable"]:
            assert str(record["reference_answer"]).startswith("REFUSE:")
    counts = {category: sum(record["category"] == category for record in records) for category in ALLOWED}
    assert counts["adversarial"] == 15
    assert counts["factoid"] >= 20
    return records


if __name__ == "__main__":
    records = validate()
    print(f"valid golden records: {len(records)}")
