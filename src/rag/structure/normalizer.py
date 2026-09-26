from pathlib import Path

from rag.ingestion import ingest_document

from .models import Document


def normalize_document(path: str) -> Document:
    file_path = Path(path)

    text = ingest_document(str(file_path))

    return Document(
        title=file_path.stem,
        source=str(file_path),
        file_type=file_path.suffix.lower().lstrip("."),
        text=text,
    )