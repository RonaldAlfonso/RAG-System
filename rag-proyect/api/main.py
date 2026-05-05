import sys
import json
sys.path.insert(0, "/app/services")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional

from retrival.rag_pipeline import ask
from retrival.retriever import hybrid_search, format_context
from retrival.country_detector import detect_country
from llm.ollama_client import generate_stream

app = FastAPI(
    title="RAG Turismo Latinoamérica",
    description="API de preguntas y respuestas sobre turismo en LATAM",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


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
        results = hybrid_search(body.query, top_k=body.top_k, filters=active_filters or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    context = format_context(results)

    def event_stream():
        # Primero enviamos metadatos y fuentes
        meta = {
            "type": "meta",
            "detected_country": detected_country,
            "filters_applied": active_filters,
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
        }
        yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"

        # Luego los tokens del LLM conforme llegan
        for token in generate_stream(query=body.query, context=context):
            yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"

        yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
