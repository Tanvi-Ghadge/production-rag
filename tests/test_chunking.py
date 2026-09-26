from rag.chunking import chunk_document
from rag.structure import Document


def test_structure_aware_chunking():
    document = Document(
        title="Test Document",
        source="test.md",
        file_type="md",
        text="""
# Introduction

This is the introduction.

## Architecture

This section explains the architecture.

## Retrieval

This section explains retrieval.
""",
    )

    chunks = chunk_document(
        document,
        chunk_size=512,
        chunk_overlap=64,
    )

    assert chunks
    assert all(chunk["text"] for chunk in chunks)

    metadata = chunks[0]["metadata"]

    assert metadata["source"] == "test.md"
    assert metadata["title"] == "Test Document"


def test_chunk_overlap_validation():
    document = Document(
        title="Test",
        source="test.md",
        file_type="md",
        text="Some text.",
    )

    try:
        chunk_document(
            document,
            chunk_size=100,
            chunk_overlap=100,
        )

        assert False, "Expected ValueError"

    except ValueError:
        pass