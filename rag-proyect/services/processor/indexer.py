import hashlib
from datetime import datetime, timezone
from typing import List
from opensearchpy import helpers
from processor.embeddigns import get_embeddings_batch
from processor.vector_store import client

INDEX_NAME = "documents"
WEB_CACHE_INDEX_NAME = "web_cache"
BATCH_SIZE = 64  # Mistral embed aguanta batches grandes; bajar a 16 si se usa Ollama

def _make_chunk_id(text: str) -> str:
    """SHA-256 del texto → ID determinista. Mismo chunk = mismo ID (dedup gratis)."""
    return hashlib.sha256(text.encode()).hexdigest()

def _make_doc_id(metadata: dict) -> str:
    """ID del documento padre basado en URL o título."""
    key = metadata.get("url") or metadata.get("title") or "unknown"
    return hashlib.sha256(key.encode()).hexdigest()

def _build_action(chunk: dict, embedding: List[float], index_name: str = INDEX_NAME) -> dict:
    """Construye una acción para el bulk API de OpenSearch."""
    chunk_id = _make_chunk_id(chunk["text"])
    return {
        "_op_type": "index",          # usa "update" si quieres upsert parcial
        "_index": index_name,
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

def index_chunks_batch(chunks: List[dict], index_name: str = INDEX_NAME):
    """
    Recibe una lista de chunks y los indexa en OpenSearch.
    Las llamadas a Ollama se hacen en sub-lotes de BATCH_SIZE para
    evitar timeouts cuando el lote total es grande.
    """
    if not chunks:
        return True

    all_actions = []
    for i in range(0, len(chunks), BATCH_SIZE):
        sub = chunks[i:i + BATCH_SIZE]
        texts = [c["text"] for c in sub]
        embeddings = get_embeddings_batch(texts)
        all_actions.extend(
            _build_action(chunk, emb, index_name)
            for chunk, emb in zip(sub, embeddings)
        )

    success, errors = helpers.bulk(
        client,
        all_actions,
        raise_on_error=False,
        stats_only=False
    )

    if errors:
        print(f"   ⚠️  {len(errors)} errores en bulk indexing:")
        for e in errors[:3]:
            print(f"      {e}")

    return success