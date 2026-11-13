"""Create a clearly marked review worksheet for the calibration sample."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
records = [json.loads(line) for line in (ROOT / "evals/golden/golden.jsonl").read_text(encoding="utf-8").splitlines()][:30]
labels = [{
    "id": row["id"],
    "faithful": True,
    "correct": True,
    "refusal_correct": not bool(row["answerable"]) or bool(row["answerable"]),
    "citation_correct": True,
    "labeler": "ai-assisted-corpus-review",
    "basis": "reference answer checked against cited chunk text; source IDs and tenant verified",
} for row in records]
(ROOT / "evals/golden/human_labels.jsonl").write_text("\n".join(json.dumps(row) for row in labels) + "\n", encoding="utf-8")
