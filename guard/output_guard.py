from __future__ import annotations


def validate_output(
    answer: dict[str, object],
    records: list[dict[str, object]],
    valid_ids: set[str] | None = None,
) -> dict[str, object]:
    if not isinstance(answer.get("answer"), str) or not isinstance(answer.get("refused"), bool):
        raise ValueError("answer schema is invalid")
    valid = valid_ids if valid_ids is not None else {str(record["chunk_id"]) for record in records}
    citations = answer.get("citations", [])
    if not isinstance(citations, list) or any(
        not isinstance(item, dict) or str(item.get("chunk_id")) not in valid
        for item in citations
    ):
        raise ValueError("answer contains an unresolved citation")
    if not answer["refused"] and not citations:
        raise ValueError("non-refusal must contain a citation")
    return answer