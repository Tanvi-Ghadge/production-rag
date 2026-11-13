"""Deterministic quality audit for the golden review queue."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
rows = [json.loads(line) for line in (ROOT / "evals/golden/golden.jsonl").read_text(encoding="utf-8").splitlines()]
index = {json.loads(line)["chunk_id"]: json.loads(line) for line in (ROOT / "data/index/chunks.jsonl").read_text(encoding="utf-8").splitlines()}
checks = {"records": len(rows), "missing_source_ids": 0, "grounded_reference_answers": 0, "bad_category_flags": 0, "version_pairs_with_two_documents": 0}
for row in rows:
    passages = [index.get(p["chunk_id"]) for p in row["source_passages"]]
    checks["missing_source_ids"] += int(any(item is None for item in passages))
    if row["answerable"] and row["category"] not in {"unanswerable", "adversarial"}:
        evidence = " ".join(item["text"] for item in passages if item)
        checks["grounded_reference_answers"] += int(row["reference_answer"] in evidence)
    if row["category"] == "adversarial":
        checks["bad_category_flags"] += int(row.get("adversarial") is not True or row["answerable"] is not False)
    if row["category"] == "version_sensitive":
        checks["version_pairs_with_two_documents"] += int(len({p["document_id"] for p in row["source_passages"]}) == 2 and len(row.get("supersession_pair", [])) == 2)
checks["automated_grounding_pass"] = checks["missing_source_ids"] == 0 and checks["grounded_reference_answers"] == 90 and checks["bad_category_flags"] == 0 and checks["version_pairs_with_two_documents"] == 15
checks["human_review_required"] = sum(row.get("review_status") != "human-reviewed" for row in rows)
checks["calibration_labels_complete"] = sum(
    all(row.get(field) is not None for field in ("faithful", "correct", "refusal_correct", "citation_correct"))
    for row in [json.loads(line) for line in (ROOT / "evals/golden/human_labels.jsonl").read_text(encoding="utf-8").splitlines()]
) == 30
(ROOT / "evals/results/golden-review.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
print(json.dumps(checks, indent=2))
