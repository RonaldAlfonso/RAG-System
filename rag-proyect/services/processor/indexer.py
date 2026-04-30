import hashlib
from datetime import datetime, timezone
from typing import List
from opensearchpy import helpers
from processor.embeddigns import get_embeddings_batch
from processor.vector_store import client

INDEX_NAME = "documents"
BATCH_SIZE = 16  # ajusta según RAM de Ollama; 16-64 es razonable

def _make_chunk_id(text: str) -> str:
    """SHA-256 del texto → ID determinista. Mismo chunk = mismo ID (dedup gratis)."""
    return hashlib.sha256(text.encode()).hexdigest()

def _make_doc_id(metadata: dict) -> str:
    """ID del documento padre basado en URL o título."""
    key = metadata.get("url") or metadata.get("title") or "unknown"
    return hashlib.sha256(key.encode()).hexdigest()

def _build_action(chunk: dict, embedding: List[float]) -> dict:
    """Construye una acción para el bulk API de OpenSearch."""
    chunk_id = _make_chunk_id(chunk["text"])
    return {
        "_op_type": "index",          # usa "update" si quieres upsert parcial
        "_index": INDEX_NAME,
        "_id": chunk_id,              # OpenSearch usa esto como _id → dedup automático
        "_source": {
            "chunk_id":    chunk_id,
            "doc_id":      _make_doc_id(chunk["metadata"]),
            "text":        chunk["text"],
            "text_keyword": chunk["text"],
            "embedding":   embedding,
            "metadata": {
                **chunk["metadata"],
                "chunk_index": chunk.get("chunk_index", 0),
                "created_at":  datetime.now(timezone.utc).isoformat()
            }
        }
    }

def index_chunks_batch(chunks: List[dict]):
    """
    Recibe una lista de chunks, llama a Ollama una sola vez
    y escribe todo en OpenSearch con el bulk API.
    """
    if not chunks:
        return

    texts = [c["text"] for c in chunks]
    embeddings = get_embeddings_batch(texts)

    actions = [
        _build_action(chunk, emb)
        for chunk, emb in zip(chunks, embeddings)
    ]

    success, errors = helpers.bulk(
        client,
        actions,
        raise_on_error=False,
        stats_only=False
    )

    if errors:
        print(f"   ⚠️  {len(errors)} errores en bulk indexing:")
        for e in errors[:3]:  # muestra solo los primeros 3
            print(f"      {e}")

    return success