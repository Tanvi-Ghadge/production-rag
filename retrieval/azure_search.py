"""Azure AI Search adapter, loaded only when the Azure backend is selected."""
from __future__ import annotations

import os
from typing import Any

from retrieval.interface import RetrievalFilters


class AzureSearchRetriever:
    def __init__(self, endpoint: str | None = None, key: str | None = None, index_name: str | None = None) -> None:
        self.endpoint = (endpoint or os.environ["AZURE_SEARCH_ENDPOINT"]).rstrip("/")
        self.key = key or os.environ["AZURE_SEARCH_ADMIN_KEY"]
        self.index_name = index_name or os.getenv("AZURE_SEARCH_INDEX", "regulatory-rag")

    def _client(self):
        from azure.search.documents import SearchClient
        from azure.core.credentials import AzureKeyCredential
        return SearchClient(self.endpoint, self.index_name, AzureKeyCredential(self.key))

    def upsert(self, chunks: list[dict[str, object]]) -> None:
        # Child chunks carry the search vector plus all isolation/version fields.
        self._client().merge_or_upload_documents(documents=chunks)

    def retrieve(self, query: str, top_k: int = 40, filters: RetrievalFilters | None = None) -> list[tuple[dict[str, object], float]]:
        clauses = []
        if filters and filters.tenant:
            clauses.append(f"tenant eq '{filters.tenant.replace("'", "''")}'")
        if filters and filters.effective_after:
            clauses.append(f"effective_date ge {filters.effective_after.isoformat()}")
        if filters and filters.effective_before:
            clauses.append(f"effective_date le {filters.effective_before.isoformat()}")
        response = self._client().search(search_text=query, filter=" and ".join(clauses) or None, top=top_k)
        return [(dict(result), float(result.get("@search.score", 0.0))) for result in response]
