from pathlib import Path

from markitdown import MarkItDown


_markitdown = MarkItDown(enable_plugins=False)


def parse_docx(path: str) -> str:
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    try:
        result = _markitdown.convert(str(file_path))
        markdown = result.markdown

        if not markdown.strip():
            raise ValueError(f"No content extracted from DOCX: {path}")

        return markdown

    except Exception as exc:
        raise ValueError(f"Could not parse DOCX: {path}") from exc