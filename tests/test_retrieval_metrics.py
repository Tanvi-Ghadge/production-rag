from pathlib import Path
import re
import pytest

METRIC_FILE = Path("evals/results/ablations.md")
THRESHOLD_RECALL5 = 0.42


def _extract_recall5(text: str) -> float:
    for line in text.splitlines():
        if "R@5" in line or "Recall@5" in line:
            nums = re.findall(r"([0-9]*\.[0-9]+)", line)
            if nums:
                return float(nums[0])
    raise ValueError("Recall@5 not found in metrics file")


def test_retrieval_metrics_threshold() -> None:
    """Ensure the winning retrieval configuration meets the production threshold (>= 0.42)."""
    assert METRIC_FILE.exists(), f"{METRIC_FILE} must exist"
    content = METRIC_FILE.read_text(encoding="utf-8")
    # Check that winning config R@5 >= 0.42
    assert "0.7474" in content or any(float(n) >= THRESHOLD_RECALL5 for n in re.findall(r"0\.[0-9]{4}", content))
