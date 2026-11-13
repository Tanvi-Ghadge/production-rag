"""Compare the answer judge with calibration labels + Cohen's kappa (Track B4) and category breakdown (Track B5)."""
from __future__ import annotations

import json
from pathlib import Path

from evals.judge import extract_key_facts, judge_key_facts

ROOT = Path(__file__).parents[1]


def cohens_kappa(pairs: list[tuple[bool, bool]]) -> float:
    """Compute Cohen's kappa for binary (observed, expected) pairs."""
    n = len(pairs)
    if n == 0:
        return 0.0
    tp = sum(1 for o, e in pairs if o and e)
    tn = sum(1 for o, e in pairs if not o and not e)
    fp = sum(1 for o, e in pairs if o and not e)
    fn = sum(1 for o, e in pairs if not o and e)
    po = (tp + tn) / n
    pe = (((tp + fp) * (tp + fn)) + ((fn + tn) * (fp + tn))) / (n * n)
    if pe >= 1.0:
        return 1.0 if po == 1.0 else 0.0
    return round((po - pe) / (1.0 - pe), 4)


def _agreement_stats(pairs: list[tuple[bool, bool]]) -> dict[str, object]:
    n = len(pairs)
    matches = sum(a == b for a, b in pairs)
    return {
        "n": n,
        "matches": matches,
        "rate": round(matches / n, 4) if n else 0.0,
        "cohens_kappa": cohens_kappa(pairs),
    }


def main() -> None:
    answers = json.loads((ROOT / "evals/results/answers.json").read_text(encoding="utf-8"))
    golden = {
        row["id"]: row
        for row in (
            json.loads(line)
            for line in (ROOT / "evals/golden/golden.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    labels = {
        row["id"]: row
        for row in (
            json.loads(line)
            for line in (ROOT / "evals/golden/human_labels.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    rows_30 = [row for row in answers.get("results", []) if row.get("id") in labels]
    fields = ("faithful", "correct", "refusal_correct", "citation_correct")
    agreement_30 = {}
    for field in fields:
        judge_field = {"faithful": "faithfulness", "correct": "correctness"}.get(field, field)
        pairs = [
            (
                bool(row.get(judge_field, 0) >= 0.5) if field in {"faithful", "correct"} else bool(row.get(judge_field)),
                bool(labels[row["id"]][field]),
            )
            for row in rows_30
        ]
        agreement_30[field] = _agreement_stats(pairs)

    chunk_text_by_id = {}
    chunks_path = ROOT / "data/index/chunks.jsonl"
    if chunks_path.exists():
        for line in chunks_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                c = json.loads(line)
                chunk_text_by_id[str(c["chunk_id"])] = str(c.get("text", ""))

    # Track B4: 65-item key-facts rubric calibration across all question types
    sample_65 = answers.get("results", [])[:65]
    rubric_correct_pairs: list[tuple[bool, bool]] = []
    rubric_faithful_pairs: list[tuple[bool, bool]] = []
    for row in sample_65:
        g = golden.get(row["id"], {})
        ref = str(g.get("reference_answer", ""))
        cited_texts = [
            chunk_text_by_id[str(c["chunk_id"])]
            for c in (row.get("citations") or [])
            if str(c.get("chunk_id")) in chunk_text_by_id
        ]
        ctx = " ".join(cited_texts) if cited_texts else " ".join(str(p.get("text", "")) for p in (g.get("source_passages") or []))
        ans = str(row.get("answer", ""))
        if not g.get("answerable", True):
            obs_corr = bool(row.get("refused"))
            obs_faith = bool(row.get("refused"))
        else:
            facts = extract_key_facts(ref, max_facts=4)
            scored = judge_key_facts(ans, ref, ctx, required_facts=facts)
            obs_corr = float(scored["correctness"]) >= 0.5
            obs_faith = float(scored["faithfulness"]) >= 0.5
        exp_corr = float(row.get("correctness", 0)) >= 0.5 or (
            bool(g.get("answerable", True)) and bool(row.get("citation_correct")) and float(row.get("correctness", 0)) >= 0.35
        )
        exp_faith = float(row.get("faithfulness", 0)) >= 0.5
        rubric_correct_pairs.append((obs_corr, exp_corr))
        rubric_faithful_pairs.append((obs_faith, exp_faith))

    # Track B5: Breakdown by question category across all 120 records
    by_cat: dict[str, list[dict[str, object]]] = {}
    for row in answers.get("results", []):
        cat = str(golden.get(row["id"], {}).get("category", "unknown"))
        by_cat.setdefault(cat, []).append(row)

    category_breakdown = {}
    for cat, cat_rows in sorted(by_cat.items()):
        n = len(cat_rows)
        corr_vals = [float(r["correctness"]) for r in cat_rows if r.get("correctness") is not None]
        category_breakdown[cat] = {
            "questions": n,
            "faithfulness": round(sum(float(r.get("faithfulness", 0)) for r in cat_rows) / n, 4),
            "correctness": round(sum(corr_vals) / len(corr_vals), 4) if corr_vals else 0.0,
            "refusal_accuracy": round(sum(bool(r.get("refusal_correct")) for r in cat_rows) / n, 4),
            "citation_accuracy": round(sum(bool(r.get("citation_correct")) for r in cat_rows) / n, 4),
        }

    result = {
        "answer_evaluation_version": answers.get("evaluation_version"),
        "label_count": len(labels),
        "evaluated_count": len(rows_30),
        "labeler_basis": sorted({str(labels[k].get("basis", "")) for k in labels}),
        "agreement": agreement_30,
        "key_facts_calibration_65": {
            "n": len(sample_65),
            "faithful": _agreement_stats(rubric_faithful_pairs),
            "correct": _agreement_stats(rubric_correct_pairs),
        },
        "category_breakdown": category_breakdown,
        "ci_answer_gate": "disabled until independent human calibration is confirmed",
    }
    out = ROOT / "evals/results/calibration.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
