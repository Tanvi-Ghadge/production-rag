from __future__ import annotations


def delimit_context(records: list[dict[str, object]]) -> str:
    return "\n\n".join(
        f"<document chunk_id={record['chunk_id']}>\n{record['text']}\n</document>"
        for record in records
    )
