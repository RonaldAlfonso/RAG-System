import sys
import json
sys.path.insert(0, "/app/services")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional

from retrival.rag_pipeline import ask
from retrival.retrieve_with_fallback import retrieve_context_with_fallback
from retrival.country_detector import detect_country
from llm.ollama_client import generate_stream

app = FastAPI(
    title="RAG Turismo Latinoamérica",
    description="API de preguntas y respuestas sobre turismo en LATAM",
    version="1.0.0",
)

@app.on_event("startup")
def _ensure_indices():
    from processor.vector_store import create_index
    create_index("documents")
    create_index("web_cache")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    query:    str  = Field(..., description="Consulta original del usuario")
    chunk_id: str  = Field(..., description="ID del chunk calificado")
    relevant: bool = Field(..., description="True = útil, False = no útil")


class AskRequest(BaseModel):
    query: str = Field(..., min_length=3, examples=["¿Qué playas hay en Colombia?"])
    top_k: int = Field(default=5, ge=1, le=20)
    filters: Optional[dict] = Field(default=None, examples=[{"pais": "Peru"}])


class Source(BaseModel):
    score: float
    text: str
    metadata: dict
    chunk_id: Optional[str]
    doc_id: Optional[str]


class AskResponse(BaseModel):
    query: str
    answer: str
    detected_country: Optional[str]
    filters_applied: dict
    sources: list[Source]
    web_fallback_attempted: bool
    web_fallback_used: bool
    web_docs_received: int
    web_chunks_indexed: int
    web_pages: list[dict]
    domain_gate_checked: bool
    domain_gate_in_domain: bool
    domain_gate_confidence: Optional[float] = None
    domain_gate_reason: Optional[str] = None
    expansion_used: bool = False
    prf_used: bool = False
    original_query: Optional[str] = None
    expanded_query_semantic: Optional[str] = None
    prf_expanded_query: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/feedback", status_code=200)
def feedback_endpoint(body: FeedbackRequest):
    """Registra la retroalimentación del usuario sobre un chunk recuperado."""
    from processor.vector_store import client as os_client
    if not os_client.indices.exists(index="feedback"):
        os_client.indices.create(
            index="feedback",
            body={
                "mappings": {
                    "properties": {
                        "query":    {"type": "text"},
                        "chunk_id": {"type": "keyword"},
                        "relevant": {"type": "boolean"},
                    }
                }
            },
            ignore=400,
        )
    os_client.index(
        index="feedback",
        body={"query": body.query, "chunk_id": body.chunk_id, "relevant": body.relevant},
    )
    return {"status": "ok", "chunk_id": body.chunk_id, "relevant": body.relevant}


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(body: AskRequest):
    try:
        result = ask(query=body.query, top_k=body.top_k, filters=body.filters)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result


@app.post("/ask/stream")
def ask_stream(body: AskRequest):
    detected_country = detect_country(body.query)
    active_filters = dict(body.filters) if body.filters else {}
    if detected_country and "pais" not in active_filters:
        active_filters["pais"] = detected_country

    try:
        retrieval = retrieve_context_with_fallback(
            query=body.query,
            top_k=body.top_k,
            filters=active_filters or None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    results = retrieval["results"]
    context = retrieval["context"]

    def event_stream():
        meta = {
            "type": "meta",
            "detected_country": detected_country,
            "filters_applied": active_filters,
            "web_fallback_attempted": retrieval.get("web_fallback_attempted", False),
            "web_fallback_used":      retrieval.get("web_fallback_used", False),
            "web_docs_received":      retrieval.get("web_docs_received", 0),
            "web_chunks_indexed":     retrieval.get("web_chunks_indexed", 0),
            "web_pages":              retrieval.get("web_pages", []),
            "domain_gate_checked":    retrieval.get("domain_gate_checked", False),
            "domain_gate_in_domain":  retrieval.get("domain_gate_in_domain", True),
            "domain_gate_confidence": retrieval.get("domain_gate_confidence", None),
            "domain_gate_reason":     retrieval.get("domain_gate_reason", None),
            "sources": [
                {
                    "score":    r["score"],
                    "text":     r["text"],
                    "metadata": r["metadata"],
                    "chunk_id": r.get("chunk_id"),
                    "doc_id":   r.get("doc_id"),
                }
                for r in results
            ],
            "expansion_used":          retrieval.get("expansion_used", False),
            "prf_used":                retrieval.get("prf_used", False),
            "original_query":          retrieval.get("original_query", body.query),
            "expanded_query_semantic": retrieval.get("expanded_query_semantic"),
            "prf_expanded_query":      retrieval.get("prf_expanded_query"),
        }
        yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"

        for token in generate_stream(query=body.query, context=context):
            yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"

        yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
