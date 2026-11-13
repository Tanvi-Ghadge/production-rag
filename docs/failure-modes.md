# Failure modes

| Failure | Behaviour | Evidence |
|---|---|---|
| Missing tenant | 422 validation failure | API contract |
| Vector backend unavailable | BM25 fallback; health degraded for external backend | `app/main.py` |
| Reranker unavailable | Retrieval continues; rerank stage marked skipped | trace |
| All LLM providers fail | 503, no uncited answer | API contract |
| Unextractable PDF | `needs_ocr`, excluded from evidence | ingest state |
| Prompt injection / PII | block/redact and refuse | `redteam.md` |
| Unknown citation | output is rejected | output guard |
