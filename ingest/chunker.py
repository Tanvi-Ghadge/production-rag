from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Iterable

from ingest.parsers.pdf import ParsedDocument


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    parent_id: str
    document_id: str
    tenant: str
    section_path: str
    text: str
    page_start: int
    page_end: int
    content_hash: str
    kind: str
    effective_date: str | None = None
    supersedes: str | None = None
    superseded_by: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def structure_aware_chunks(
    document: ParsedDocument,
    document_id: str,
    tenant: str,
    child_words: int = 400,
    overlap_words: int = 50,
    effective_date: str | None = None,
    supersedes: str | None = None,
    superseded_by: str | None = None,
) -> list[Chunk]:
    """Create section parents and token-window children.

    ``child_words``/``overlap_words`` are retained as public argument names for
    compatibility; their values are token counts, not whitespace-word counts.
    The lightweight tokenizer is deterministic and does not require a model at
    ingest time.
    """
    if child_words <= overlap_words:
        raise ValueError("child_words must be greater than overlap_words")
    chunks: list[Chunk] = []
    for page in document.pages:
        if not page.text:
            continue
        sections = _sections(page.text)
        for section_index, (heading, body) in enumerate(sections):
            section_path = heading or f"page-{page.page_number}"
            parent_id = _id(document_id, "parent", page.page_number, section_index, body)
            chunks.append(Chunk(parent_id, parent_id, document_id, tenant, section_path, body,
                                page.page_number, page.page_number, _hash(body), "parent",
                                effective_date, supersedes, superseded_by))
            tokens = _tokens(body)
            step = child_words - overlap_words
            # Table-like sections deliberately stay intact: splitting a row can
            # turn a regulatory limit into an incorrect answer.
            windows = [(0, tokens)] if _is_table_like(body) else [
                (offset, tokens[offset : offset + child_words])
                for offset in range(0, len(tokens), step)
            ]
            for offset, window in windows:
                text = " ".join(window).strip()
                if not text:
                    continue
                chunk_id = _id(document_id, "child", page.page_number, section_index, offset, text)
                chunks.append(Chunk(chunk_id, parent_id, document_id, tenant, section_path, text,
                                    page.page_number, page.page_number, _hash(text), "child",
                                    effective_date, supersedes, superseded_by))
                if offset + child_words >= len(tokens):
                    break
    return chunks


def _sections(text: str) -> Iterable[tuple[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    heading = ""
    body: list[str] = []
    for line in lines:
        is_heading = len(line) <= 120 and (
            re.match(r"^(?:\d+(?:\.\d+)*|[A-Z])[\.)\s]", line) or line.isupper()
        )
        if is_heading and body:
            yield heading, " ".join(body)
            body = []
        if is_heading:
            heading = line
        else:
            body.append(line)
    if body:
        yield heading, " ".join(body)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _id(*parts: object) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:24]


def _tokens(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def _is_table_like(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    signals = sum(
        bool(re.search(r"(?:₹|Rs\.?|T\s*\+\s*\d|Annex(?:ure)?|\b(?:days?|hours?)\b|\d+\s*%)", line, re.I))
        for line in lines
    )
    return signals >= 2 or (len(lines) >= 3 and sum(bool(re.search(r"\d", line)) for line in lines) >= 3)
