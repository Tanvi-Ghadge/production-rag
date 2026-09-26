from pathlib import Path

from .docx_parser import parse_docx
from .markdown_parser import parse_markdown
from .pdf_parser import parse_pdf
from .txt_parser import parse_txt


SUPPORTED_EXTENSIONS = {
    ".txt": parse_txt,
    ".md": parse_markdown,
    ".pdf": parse_pdf,
    ".docx": parse_docx,
}


def ingest_document(path: str) -> str:
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    extension = file_path.suffix.lower()

    parser = SUPPORTED_EXTENSIONS.get(extension)

    if parser is None:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))

        raise ValueError(
            f"Unsupported file type: {extension}. "
            f"Supported types: {supported}"
        )

    return parser(str(file_path))