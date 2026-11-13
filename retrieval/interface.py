from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class RetrievalFilters:
    tenant: str | None = None
    effective_after: date | None = None
    effective_before: date | None = None


class Retriever(Protocol):
    def retrieve(
        self, query: str, top_k: int = 40, filters: RetrievalFilters | None = None
    ) -> list[tuple[dict[str, object], float]]:
        ...


def matches_filters(document: dict[str, object], filters: RetrievalFilters | None) -> bool:
    if filters is None:
        return True
    if filters.tenant is not None and document.get("tenant") != filters.tenant:
        return False
    effective_date = document.get("effective_date")
    if effective_date is None:
        return filters.effective_after is None and filters.effective_before is None
    parsed = date.fromisoformat(str(effective_date))
    if filters.effective_after is not None and parsed < filters.effective_after:
        return False
    if filters.effective_before is not None and parsed > filters.effective_before:
        return False
    return True
