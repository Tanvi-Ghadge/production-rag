"""CI regression gate.

Reads ablations_lean.json (or ablations.json) for retrieval metrics and
answers.json for generation metrics. Fails if recall@5 drops >3pp from
the committed baseline or if faithfulness/citation/refusal drop >3pp.

Runs on dev split metrics only.
"""
from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).parents[1]
    results_dir = root / "evals" / "results"

    # ── Retrieval gate ────────────────────────────────────────────────────────
    # Prefer lean ablations (dev split), fall back to full ablations
    abl_path = results_dir / "ablations_lean.json"
    if not abl_path.exists():
        abl_path = results_dir / "ablations.json"

    ablations = json.loads(abl_path.read_text())
    best_r5 = max(r["recall@5"] for r in ablations)

    # Committed baseline (best R@5 on the clean dev set, set after first clean run)
    baseline_path = results_dir / "baseline.json"
    if baseline_path.exists():
        baseline_payload = json.loads(baseline_path.read_text())
        baseline_r5 = float(
            baseline_payload["recall@5"] if isinstance(baseline_payload, dict) else baseline_payload
        )
        drop = baseline_r5 - best_r5
        if drop > 0.03:
            raise SystemExit(
                f"recall@5 dropped by {drop:.4f} "
                f"(current {best_r5:.4f} vs baseline {baseline_r5:.4f})"
            )

    # ── Generation gate ───────────────────────────────────────────────────────
    answers_path = results_dir / "answers.json"
    if answers_path.exists():
        answers = json.loads(answers_path.read_text())
        required = {"questions", "results", "faithfulness", "citation_accuracy", "refusal_accuracy", "schema_valid"}
        if not required <= answers.keys() or len(answers["results"]) != int(answers["questions"]):
            raise SystemExit("answer evaluation is incomplete")
        if not answers["schema_valid"]:
            raise SystemExit("answer schema validation failed")
        answer_baseline_path = results_dir / "answer-baseline.json"
        if answer_baseline_path.exists():
            answer_baseline = json.loads(answer_baseline_path.read_text())
            thresholds = {
                "faithfulness": float(answer_baseline["faithfulness"]),
                "citation_accuracy": float(answer_baseline["citation_accuracy"]),
                "refusal_accuracy": float(answer_baseline["refusal_accuracy"]),
            }
            for metric, minimum in thresholds.items():
                if minimum - float(answers[metric]) > 0.03:
                    raise SystemExit(
                        f"{metric} dropped by more than 0.03: {answers[metric]} < {minimum}"
                    )
        gen_metrics = {m: answers[m] for m in ["faithfulness", "citation_accuracy", "refusal_accuracy"]}
    else:
        gen_metrics = {"answers.json": "not found — skipping generation gate"}

    result = {"recall@5": best_r5, **gen_metrics}
    print(result)


if __name__ == "__main__":
    main()
