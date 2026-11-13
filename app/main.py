from __future__ import annotations

from contextlib import asynccontextmanager
import json
import os
import asyncio
from collections import defaultdict, deque
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock
from functools import lru_cache
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from guard.input_guard import UnsupportedQuestionError, check_input
from guard.output_guard import validate_output
from ingest.indexer import LocalIndex
from ingest.parsers.pdf import parse_pdf
from query.assemble import assemble_context
from query.generate import generate_answer
from query.rewrite import rewrite_query
from retrieval.interface import RetrievalFilters
from observability.tracing import Trace
from time import perf_counter

ROOT = Path(__file__).parents[1]
load_dotenv(ROOT / ".env", override=True)
INDEX = LocalIndex(ROOT / "data" / "index")
API_KEYS = {key.strip() for key in os.getenv("RAG_API_KEYS", "dev-key").split(",") if key.strip()}
_requests: dict[str, deque[datetime]] = defaultdict(deque)
_jobs: dict[str, dict[str, object]] = {}
_lock = Lock()
ASK_TIMEOUT_SECONDS = float(os.getenv("RAG_ASK_TIMEOUT_SECONDS", "90"))
ASK_RATE_LIMIT = int(os.getenv("RAG_ASK_RATE_LIMIT", "60"))

_startup_metrics: dict[str, float] = {}


@asynccontextmanager
async def _lifespan(_: FastAPI):
    t0 = perf_counter()
    _records()
    _tenant_indexes()
    _bm25()
    retriever = _retriever()
    reranker = _reranker()
    # Warm up embedder + pgvector connection + reranker so the first request isn't cold.
    try:
        dummy_results = retriever.retrieve("warmup query", top_k=2, filters=RetrievalFilters("A"))
        reranker.rerank("warmup query", dummy_results, top_k=1)
    except Exception:
        pass
    _startup_metrics["cold_start_ms"] = round((perf_counter() - t0) * 1000.0, 3)
    yield


app = FastAPI(title="Regulatory RAG API", version="1.0", lifespan=_lifespan)


class HistoryItem(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str
    tenant: str
    history: list[HistoryItem] = Field(default_factory=list)
    effective_after: date | None = None
    effective_before: date | None = None


class FeedbackRequest(BaseModel):
    trace_id: str
    rating: str
    comment: str | None = None


def _authenticate(key: str | None) -> None:
    if key not in API_KEYS:
        raise HTTPException(status_code=401, detail="invalid API key")
    now = datetime.now(timezone.utc)
    with _lock:
        window = _requests[key]
        while window and (now - window[0]).total_seconds() >= 60:
            window.popleft()
        if len(window) >= ASK_RATE_LIMIT:
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        window.append(now)


@lru_cache(maxsize=1)
def _retriever():
    from ingest.embedder import SentenceTransformerEmbedder
    embedder = SentenceTransformerEmbedder(
        ROOT / "data" / "index" / "query-cache.json",
        persist_cache=False,
    )
    if os.getenv("RAG_RETRIEVER", "local") == "pgvector":
        from retrieval.pgvector import PgVectorRetriever
        return PgVectorRetriever(
            os.getenv("PGVECTOR_DSN", "postgresql://rag:rag@localhost:55432/rag"),
            embedder,
        )
    if os.getenv("RAG_RETRIEVER") == "azure":
        from retrieval.azure_search import AzureSearchRetriever
        return AzureSearchRetriever()
    return INDEX.hybrid(embedder)


@lru_cache(maxsize=1)
def _reranker():
    from retrieval.rerank import CrossEncoderReranker
    return CrossEncoderReranker()


@lru_cache(maxsize=1)
def _records() -> list[dict[str, object]]:
    return INDEX.load_chunks()


@lru_cache(maxsize=1)
def _bm25():
    from retrieval.bm25 import BM25Index
    return BM25Index(_records())


@lru_cache(maxsize=1)
def _tenant_indexes() -> dict[str | None, tuple[list[dict[str, object]], dict[str, dict[str, object]], set[str]]]:
    all_records = _records()
    grouped: dict[str | None, list[dict[str, object]]] = {None: all_records}
    for record in all_records:
        grouped.setdefault(record.get("tenant"), []).append(record)
    return {
        tenant: (
            items,
            {str(item["chunk_id"]): item for item in items},
            {str(item["chunk_id"]) for item in items},
        )
        for tenant, items in grouped.items()
    }


@app.get("/v1/health")
def health() -> dict[str, object]:
    state = INDEX.state_path.exists()
    result: dict[str, object] = {
        "status": "ok",
        "retriever": os.getenv("RAG_RETRIEVER", "local"),
        "index": state,
        "chunks": len(_records()),
        **_startup_metrics,
    }
    if result["retriever"] == "pgvector":
        try:
            import psycopg
            with psycopg.connect(os.getenv("PGVECTOR_DSN", "postgresql://rag:rag@localhost:55432/rag")) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT count(*) FROM chunks")
                    result["pgvector_chunks"] = cursor.fetchone()[0]
        except Exception as exc:
            result["status"] = "degraded"
            result["pgvector_error"] = str(exc)
    return result


def _ask_payload(request: AskRequest) -> dict[str, object]:
    trace = Trace()
    try:
        with trace.stage("input_guard"):
            question = check_input(request.question)
    except UnsupportedQuestionError:
        return {
            "trace_id": trace.trace_id,
            "query": request.question,
            "trace": trace.stages,
            "answer": "I cannot answer this because it is outside the regulatory corpus.",
            "refused": True,
            "citations": [],
            "cache_hit": False,
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with trace.stage("rewrite"):
        rewritten = rewrite_query(question, [item.model_dump() for item in request.history])
    with trace.stage("retrieve"):
        filters = RetrievalFilters(request.tenant, request.effective_after, request.effective_before)
        try:
            results = _retriever().retrieve(
                rewritten,
                top_k=int(os.getenv("RAG_RERANK_CANDIDATES", "20")),
                filters=filters,
            )
        except Exception:
            # The local lexical index remains a useful, observable degradation
            # path when the configured vector backend is unavailable.
            results = _bm25().search(rewritten, int(os.getenv("RAG_RERANK_CANDIDATES", "20")), filters)
            trace.stages["retrieve_fallback"] = {"latency_ms": 0.0, "tokens": 0, "cost": 0.0}
    with trace.stage("rerank"):
        skip_rerank = os.getenv("RAG_SKIP_RERANKER") == "1"
        if not skip_rerank:
            try:
                results = _reranker().rerank(rewritten, results, top_k=10)
            except Exception:
                skip_rerank = True
    if skip_rerank:
        trace.stages["rerank"]["skipped"] = 1
    with trace.stage("assemble"):
        records, by_id, valid_ids = _tenant_indexes().get(request.tenant, ([], {}, set()))
        context = assemble_context(results, records, by_id=by_id)
    with trace.stage("generate"):
        try:
            answer = validate_output(generate_answer(context, rewritten), records, valid_ids=valid_ids)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=f"answer provider unavailable: {exc}") from exc
    trace.stages["generate"]["tokens"] = int(answer.get("completion_tokens", 0))
    trace.stages["generate"]["cost"] = float(answer.get("cost", 0.0))
    return {"trace_id": trace.trace_id, "query": rewritten, "trace": trace.stages, **answer}


@app.post("/v1/ask")
async def ask(request: AskRequest, x_api_key: str | None = Header(default=None)) -> StreamingResponse:
    _authenticate(x_api_key)
    try:
        value = await asyncio.wait_for(asyncio.to_thread(_ask_payload, request), timeout=ASK_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="answer request timed out") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"answer service failed: {exc}") from exc

    def stream():
        # Extractive/fallback output is still sent incrementally, making the
        # endpoint a real SSE stream rather than one process-sized blob.
        for token in str(value["answer"]).split():
            yield f"event: token\ndata: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        yield f"event: final\ndata: {json.dumps(value, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream")


def _run_ingest(job_id: str, path: Path, tenant: str) -> None:
    try:
        parsed = parse_pdf(path)
        if not parsed.text:
            raise ValueError("PDF has no extractable text; OCR is required")
        from ingest.chunker import structure_aware_chunks
        from ingest.embedder import SentenceTransformerEmbedder

        chunks = structure_aware_chunks(parsed, job_id, tenant)
        embedder = SentenceTransformerEmbedder(ROOT / "data" / "index" / "embedding-cache.json")
        changed, total = INDEX.upsert(chunks, embedder)
        _retriever.cache_clear()
        _records.cache_clear()
        _bm25.cache_clear()
        _tenant_indexes.cache_clear()
        _jobs[job_id] = {
            "status": "completed",
            "text_pages": len(parsed.pages),
            "tenant": tenant,
            "chunks": len(chunks),
            "changed_chunks": changed,
            "total_chunks": total,
        }
    except Exception as exc:
        _jobs[job_id] = {"status": "failed", "error": str(exc)}


@app.post("/v1/ingest", status_code=202)
async def ingest(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    tenant: str = Form(...),
    x_api_key: str | None = Header(default=None),
) -> dict[str, str]:
    _authenticate(x_api_key)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="only PDF uploads are supported")
    job_id = uuid4().hex
    path = ROOT / "data" / "incoming" / f"{job_id}.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(await file.read())
    _jobs[job_id] = {"status": "queued"}
    background.add_task(_run_ingest, job_id, path, tenant)
    return {"job_id": job_id}


@app.get("/v1/ingest/{job_id}")
def ingest_status(job_id: str, x_api_key: str | None = Header(default=None)) -> dict[str, object]:
    _authenticate(x_api_key)
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="job not found")
    return {"job_id": job_id, **_jobs[job_id]}


@app.post("/v1/feedback")
def feedback(request: FeedbackRequest, x_api_key: str | None = Header(default=None)) -> dict[str, object]:
    _authenticate(x_api_key)
    if request.rating not in {"up", "down"}:
        raise HTTPException(status_code=422, detail="rating must be up or down")
    return {"accepted": True, **request.model_dump()}
