from __future__ import annotations


def assemble_context(
    results: list[tuple[dict[str, object], float]],
    records: list[dict[str, object]],
    max_words: int = 2400,
    by_id: dict[str, dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    lookup = by_id if by_id is not None else {str(record["chunk_id"]): record for record in records}
    selected: list[dict[str, object]] = []
    seen: set[str] = set()
    words = 0
    for result, score in results:
        child_id = str(result["chunk_id"])
        parent_id = str(result.get("parent_id", child_id))
        parent = lookup.get(parent_id)
        record = parent if parent and parent.get("tenant") == result.get("tenant") else result
        key = str(record["chunk_id"])
        if key in seen:
            continue
        text = str(record.get("text", ""))
        count = len(text.split())
        if words + count > max_words:
            break
        selected.append({"chunk": record, "score": score})
        seen.add(key)
        words += count
    return selected
