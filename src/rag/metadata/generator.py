from dataclasses import dataclass

from rag.metadata.models import ChunkMetadataResult
from rag.metadata.providers.groq import (
    generate_metadata_batch,
)


DEFAULT_BATCH_SIZE = 5
DEFAULT_MAX_RETRIES = 3


@dataclass
class MetadataFailure:
    chunk_ids: list[str]
    error: str


@dataclass
class MetadataGenerationResult:
    chunks: list[dict]
    failures: list[MetadataFailure]


def _attach_metadata(
    chunk: dict,
    metadata: ChunkMetadataResult,
) -> dict:
    return {
        **chunk,
        "metadata": {
            **chunk["metadata"],
            "summary": metadata.summary,
            "keywords": metadata.keywords,
            "hypothetical_question": (
                metadata.hypothetical_question
            ),
        },
    }


def _validate_batch_results(
    chunks: list[dict],
    results: list[ChunkMetadataResult],
) -> dict[str, ChunkMetadataResult]:

    expected_ids = {
        chunk["metadata"]["chunk_id"]
        for chunk in chunks
    }

    result_map: dict[
        str,
        ChunkMetadataResult,
    ] = {}

    for result in results:

        if result.chunk_id in result_map:
            raise ValueError(
                f"Duplicate metadata returned for "
                f"chunk_id: {result.chunk_id}"
            )

        result_map[result.chunk_id] = result

    returned_ids = set(result_map)

    missing_ids = expected_ids - returned_ids
    unexpected_ids = returned_ids - expected_ids

    if missing_ids:
        raise ValueError(
            f"Missing metadata for chunks: "
            f"{sorted(missing_ids)}"
        )

    if unexpected_ids:
        raise ValueError(
            f"Unexpected chunk IDs returned: "
            f"{sorted(unexpected_ids)}"
        )

    return result_map


def enrich_chunks(
    chunks: list[dict],
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> MetadataGenerationResult:
    """
    Generate metadata for chunks in request-level batches.

    Failed batches are recorded and processing continues
    with subsequent batches.
    """

    if batch_size <= 0:
        raise ValueError(
            "batch_size must be greater than 0"
        )

    if max_retries < 0:
        raise ValueError(
            "max_retries cannot be negative"
        )

    enriched_chunks: list[dict] = []
    failures: list[MetadataFailure] = []

    for start in range(
        0,
        len(chunks),
        batch_size,
    ):

        batch = chunks[
            start:start + batch_size
        ]

        batch_ids = [
            chunk["metadata"]["chunk_id"]
            for chunk in batch
        ]

        print(
            f"Processing metadata batch "
            f"{start // batch_size + 1}: "
            f"{len(batch)} chunks"
        )

        try:

            results = generate_metadata_batch(
                batch,
                max_retries=max_retries,
            )

            result_map = _validate_batch_results(
                batch,
                results,
            )

            for chunk in batch:

                chunk_id = (
                    chunk["metadata"]["chunk_id"]
                )

                enriched_chunks.append(
                    _attach_metadata(
                        chunk,
                        result_map[chunk_id],
                    )
                )

        except Exception as exc:

            failures.append(
                MetadataFailure(
                    chunk_ids=batch_ids,
                    error=str(exc),
                )
            )

            print(
                f"Metadata batch failed permanently "
                f"for chunks: {batch_ids}"
            )

    return MetadataGenerationResult(
        chunks=enriched_chunks,
        failures=failures,
    )


def enrich_chunk(chunk: dict) -> dict:
    """
    Convenience function for processing one chunk.
    """

    result = enrich_chunks(
        [chunk],
        batch_size=1,
    )

    if result.failures:
        raise RuntimeError(
            result.failures[0].error
        )

    return result.chunks[0]