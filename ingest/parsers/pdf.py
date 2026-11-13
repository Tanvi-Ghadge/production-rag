from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from pypdf import PdfReader


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    path: str
    pages: tuple[ParsedPage, ...]
    text: str


def parse_pdf(path: Path) -> ParsedDocument:
    reader = PdfReader(str(path))
    pages = tuple(
        ParsedPage(index + 1, _clean_text(page.extract_text() or ""))
        for index, page in enumerate(reader.pages)
    )
    return ParsedDocument(str(path), pages, "\n\n".join(p.text for p in pages if p.text))


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
