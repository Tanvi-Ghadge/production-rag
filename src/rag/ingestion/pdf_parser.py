from pathlib import Path

import pymupdf4llm


def parse_pdf(path: str) -> str:
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    try:
        markdown = pymupdf4llm.to_markdown(
            str(file_path),
            header=False,
            footer=False,
        )

        if not markdown.strip():
            raise ValueError(f"No content extracted from PDF: {path}")

        return markdown

    except Exception as exc:
        raise ValueError(f"Could not parse PDF: {path}") from exc