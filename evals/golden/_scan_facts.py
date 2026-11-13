"""Print fact-bearing sentences from the frozen corpus. Local authoring aid."""
from __future__ import annotations

import csv
import re
from pathlib import Path

from ingest.parsers.pdf import parse_pdf

ROOT = Path(__file__).parents[2]
PAT = re.compile(
    r"(?i)(?:₹|rs\.?\s?\d|\b\d+(?:\.\d+)?\s*(?:%|percent|lakh|crore|days?)\b|\bshall\b|\bT\s*\+\s*\d)"
)


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.])\s+", text.replace("\n", " "))
    return [part.strip() for part in parts if 80 <= len(part) <= 320 and PAT.search(part)]


def main() -> None:
    rows = list(csv.DictReader((ROOT / "corpus" / "audit.csv").open(encoding="utf-8")))
    out = ROOT / "evals" / "golden" / "_facts.txt"
    lines: list[str] = []
    for row in rows:
        path = ROOT / "corpus" / "raw" / row["tenant"] / row["file"]
        text = parse_pdf(path).text or ""
        picked = sentences(text)[:8]
        lines.append(f"## {row['tenant']}/{row['file']} tables={row['tables']} chars={len(text)}")
        for sentence in picked:
            lines.append(sentence)
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out} lines={len(lines)}")


if __name__ == "__main__":
    main()
