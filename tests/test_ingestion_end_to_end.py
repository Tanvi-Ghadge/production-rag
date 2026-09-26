from pathlib import Path

from rag.chunking import chunk_document
from rag.metadata import enrich_chunks
from rag.structure import normalize_document


TEST_FILES = [
    "data/raw/Q3_2026_business_review.pdf",
]


def test_end_to_end_ingestion():
    for file_path in TEST_FILES:

        # -------------------------------------------------
        # 1. Normalize / ingest
        # -------------------------------------------------

        document = normalize_document(file_path)

        assert document.text
        assert document.title
        assert document.source
        assert document.file_type

        print(
            f"\nDocument: {document.title}"
        )

        print(
            f"File type: {document.file_type}"
        )

        print(
            f"Extracted characters: "
            f"{len(document.text)}"
        )

        # -------------------------------------------------
        # 2. Chunk
        # -------------------------------------------------

        chunks = chunk_document(document)

        assert chunks
        assert len(chunks) > 0

        print(
            f"Chunks created: {len(chunks)}"
        )

        # -------------------------------------------------
        # 3. Validate raw chunks
        # -------------------------------------------------

        chunk_ids = set()

        for chunk in chunks:

            assert chunk["text"].strip()

            assert "metadata" in chunk

            metadata = chunk["metadata"]

            assert metadata["source"] == document.source
            assert metadata["title"] == document.title
            assert metadata["file_type"] == document.file_type

            assert "chunk_id" in metadata

            chunk_id = metadata["chunk_id"]

            assert chunk_id not in chunk_ids

            chunk_ids.add(chunk_id)

        assert len(chunk_ids) == len(chunks)

        print(
            "Raw chunk validation: PASSED"
        )

        # -------------------------------------------------
        # 4. Generate metadata
        # -------------------------------------------------

        result = enrich_chunks(
            chunks,
            batch_size=5,
            max_retries=3,
        )

        # -------------------------------------------------
        # 5. Validate failures
        # -------------------------------------------------

        assert not result.failures, (
            f"Metadata generation failed: "
            f"{result.failures}"
        )

        # -------------------------------------------------
        # 6. Validate final enriched chunks
        # -------------------------------------------------

        enriched_chunks = result.chunks

        assert enriched_chunks
        assert len(enriched_chunks) == len(chunks)

        for chunk in enriched_chunks:

            assert chunk["text"].strip()

            metadata = chunk["metadata"]

            # Original metadata
            assert "chunk_id" in metadata
            assert "source" in metadata
            assert "title" in metadata
            assert "file_type" in metadata

            # Generated metadata
            assert "summary" in metadata
            assert metadata["summary"].strip()

            assert "keywords" in metadata
            assert isinstance(
                metadata["keywords"],
                list,
            )
            assert len(metadata["keywords"]) > 0

            assert "hypothetical_question" in metadata
            assert metadata[
                "hypothetical_question"
            ].strip()

        print(
            "Enriched chunk validation: PASSED"
        )

        # -------------------------------------------------
        # 7. Verify chunk IDs survived metadata generation
        # -------------------------------------------------

        enriched_ids = {
            chunk["metadata"]["chunk_id"]
            for chunk in enriched_chunks
        }

        assert enriched_ids == chunk_ids

        print(
            "Chunk ID preservation: PASSED"
        )

        # -------------------------------------------------
        # 8. Final result
        # -------------------------------------------------

        print("\n" + "=" * 60)
        print("END-TO-END INGESTION TEST PASSED")
        print("=" * 60)

        print(
            f"Document: {document.title}"
        )

        print(
            f"Chunks: {len(chunks)}"
        )

        print(
            f"Enriched chunks: "
            f"{len(enriched_chunks)}"
        )

        print(
            f"Failures: "
            f"{len(result.failures)}"
        )

        print("=" * 60)