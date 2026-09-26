from pathlib import Path

import pytest

from rag.ingestion import ingest_document


def test_ingest_txt(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text(
        "This is a sample text document.",
        encoding="utf-8",
    )

    result = ingest_document(str(path))

    assert isinstance(result, str)
    assert result == "This is a sample text document."


def test_ingest_markdown(tmp_path):
    path = tmp_path / "sample.md"
    path.write_text(
        "# Introduction\n\nThis is a sample Markdown document.",
        encoding="utf-8",
    )

    result = ingest_document(str(path))

    assert isinstance(result, str)
    assert "# Introduction" in result
    assert "sample Markdown document" in result


def test_ingest_pdf():
    """
    PDF integration test against an actual corpus document.
    Skip if the corpus file is not available.
    """

    path = Path("data/raw/Q3_2026_business_review.pdf")

    if not path.exists():
        pytest.skip("Business review PDF not available")

    result = ingest_document(str(path))

    assert isinstance(result, str)
    assert result.strip()
    assert "# " in result


def test_ingest_docx(tmp_path):
    """
    Create a minimal DOCX and verify MarkItDown can ingest it.
    """

    from docx import Document

    path = tmp_path / "sample.docx"

    document = Document()
    document.add_heading("Introduction", level=1)
    document.add_paragraph(
        "This is a sample DOCX document."
    )
    document.save(path)

    result = ingest_document(str(path))

    assert isinstance(result, str)
    assert result.strip()
    assert "Introduction" in result
    assert "sample DOCX document" in result


def test_unsupported_extension(tmp_path):
    path = tmp_path / "test.png"
    path.write_bytes(b"fake image")

    with pytest.raises(
        ValueError,
        match="Unsupported file type",
    ):
        ingest_document(str(path))