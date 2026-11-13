# Week 9 API core

Run locally with:

```text
uvicorn app.main:app --reload
```

Set `RAG_API_KEYS` to a comma-separated list before serving. Requests to
`/v1/ask`, `/v1/ingest`, `/v1/ingest/{job_id}`, and `/v1/feedback` require
`X-API-Key`; `/v1/health` is public. Each key is limited to 60 requests per
minute in the process.

`/v1/ask` returns Server-Sent Events containing a cited JSON answer. It rewrites
the question with recent history, applies tenant filtering, expands child hits
to parent sections, deduplicates them, and enforces a 2,400-word context limit.
When no evidence is retrieved it returns a cited refusal.

The current generator is extractive and deterministic. Provider-backed
generation, response caching, tracing, and external rate-limit storage remain
separate Week 9 tasks.

To use Cohere Command R locally, set the secret in the shell and select
pgvector:

```powershell
$env:COHERE_API_KEY="paste-your-key-here"
$env:COHERE_MODEL="command-r-08-2024"
$env:RAG_RETRIEVER="pgvector"
$env:PGVECTOR_DSN="postgresql://rag:rag@localhost:55432/rag"
uvicorn app.main:app --reload
```

The same Compose stack starts Redis on `localhost:6379` for the exact response
cache. `REDIS_URL` can be left empty for an in-memory cache, but the checked-in
local `.env` enables Redis.
