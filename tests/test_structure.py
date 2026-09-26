from pathlib import Path

from rag.structure import Document, normalize_document


def test_normalize_pdf():
    path = Path("data/raw/Q3_2026_business_review.pdf")

    if not path.exists():
        return

    document = normalize_document(str(path))

    assert isinstance(document, Document)
    assert document.file_type == "pdf"
    assert document.text.strip()


def test_normalize_markdown(tmp_path):
    path = tmp_path / "sample.md"

    path.write_text(
        "# Introduction\n\n"
        "This is a Markdown document.\n\n"
        "## Architecture\n\n"
        "This section explains the architecture.",
        encoding="utf-8",
    )

    document = normalize_document(str(path))

    assert isinstance(document, Document)
    assert document.file_type == "md"
    assert "# Introduction" in document.text
    assert "## Architecture" in document.text