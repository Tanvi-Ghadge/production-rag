import json
import os
import time

from dotenv import load_dotenv
from groq import (
    APIConnectionError,
    APITimeoutError,
    Groq,
    InternalServerError,
    RateLimitError,
)

from rag.metadata.models import (
    ChunkMetadataResult,
    MetadataBatchResponse,
)


load_dotenv()


MODEL_NAME = "openai/gpt-oss-20b"


METADATA_BATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "chunk_id": {
                        "type": "string",
                    },
                    "summary": {
                        "type": "string",
                    },
                    "keywords": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                    "hypothetical_question": {
                        "type": "string",
                    },
                },
                "required": [
                    "chunk_id",
                    "summary",
                    "keywords",
                    "hypothetical_question",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}


def _build_prompt(chunks: list[dict]) -> str:
    parts = [
        (
            "Generate metadata for each RAG document chunk below.\n\n"
            "For every chunk:\n"
            "- Write a concise factual summary.\n"
            "- Extract the most important keywords.\n"
            "- Generate one question that the chunk can answer.\n"
            "- Use only information present in that chunk.\n"
            "- Preserve the exact chunk_id provided.\n\n"
            "Return exactly one metadata result for every chunk.\n"
        )
    ]

    for chunk in chunks:
        parts.append(
            f"\n--- CHUNK {chunk['metadata']['chunk_id']} ---\n"
            f"{chunk['text']}\n"
        )

    return "".join(parts)


def _is_retryable_error(exc: Exception) -> bool:
    """
    Only retry transient failures.
    """

    return isinstance(
        exc,
        (
            RateLimitError,
            APIConnectionError,
            APITimeoutError,
            InternalServerError,
        ),
    )


def _get_retry_delay(
    exc: Exception,
    attempt: int,
) -> float:
    """
    Prefer the provider's retry-after value.

    Otherwise use exponential backoff:

        attempt 0 -> 1 second
        attempt 1 -> 2 seconds
        attempt 2 -> 4 seconds

    Maximum fallback delay: 30 seconds.
    """

    response = getattr(exc, "response", None)

    if response is not None:
        headers = getattr(
            response,
            "headers",
            {},
        )

        retry_after = headers.get("retry-after")

        if retry_after:
            try:
                return float(retry_after)
            except (TypeError, ValueError):
                pass

    return min(2 ** attempt, 30)


def generate_metadata_batch(
    chunks: list[dict],
    max_retries: int = 3,
) -> list[ChunkMetadataResult]:
    """
    Generate metadata for multiple chunks using one API request.

    Only transient failures are retried.
    """

    if not chunks:
        return []

    if max_retries < 0:
        raise ValueError(
            "max_retries cannot be negative."
        )

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not set in the environment."
        )

    client = Groq(api_key=api_key)

    prompt = _build_prompt(chunks)

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You generate concise, factual metadata "
                            "for RAG document chunks."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "chunk_metadata_batch",
                        "strict": True,
                        "schema": METADATA_BATCH_SCHEMA,
                    },
                },
            )

            content = response.choices[0].message.content

            if not content:
                raise ValueError(
                    "Groq returned an empty response."
                )

            data = json.loads(content)

            batch_response = (
                MetadataBatchResponse.model_validate(data)
            )

            return batch_response.results

        except Exception as exc:

            if not _is_retryable_error(exc):
                raise

            if attempt >= max_retries:
                raise

            delay = _get_retry_delay(
                exc,
                attempt,
            )

            print(
                f"Metadata batch failed "
                f"(attempt {attempt + 1}/{max_retries + 1}). "
                f"Retrying in {delay:.1f}s..."
            )

            time.sleep(delay)

    raise RuntimeError(
        "Metadata generation failed unexpectedly."
    )