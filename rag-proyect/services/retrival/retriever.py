from typing import List, Dict, Optional
from processor.vector_store import client
from processor.embeddigns import get_embedding
from processor.indexer import INDEX_NAME, WEB_CACHE_INDEX_NAME

PIPELINE_ID = "hybrid-pipeline"

COUNTRY_BOOST    = 1.5   # impulso para documentos del país detectado en la consulta
FEEDBACK_BOOST   = 1.2   # impulso para documentos con retroalimentación positiva
CANDIDATE_FACTOR = 3     # cuántos candidatos extra recuperar antes de aplicar boosts

def _load_feedback_index() -> Dict[str, bool]:
    """Devuelve {chunk_id: True/False} con la retroalimentación almacenada."""
    try:
        resp = client.search(
            index="feedback",
            body={"size": 10000, "_source": ["chunk_id", "relevant"]},
        )
        return {
            h["_source"]["chunk_id"]: h["_source"]["relevant"]
            for h in resp["hits"]["hits"]
            if "chunk_id" in h["_source"]
        }
    except Exception:
        return {}

def hybrid_search(
    query: str,
    top_k: int = 5,
    filters: Optional[Dict] = None,
    index_name: str = INDEX_NAME,
) -> List[Dict]:
    query_vector = get_embedding(query)

    # País detectado para el impulso de ranking (puede venir en filters)
    detected_country = (filters or {}).get("pais")

    # Recuperar más candidatos para luego aplicar los factores de ranking
    fetch_k = top_k * CANDIDATE_FACTOR

    body = {
        "size": fetch_k,
        "query": {
            "hybrid": {
                "queries": [
                    {"match": {"text": {"query": query}}},
                    {"knn": {"embedding": {"vector": query_vector, "k": fetch_k}}}
                ]
            }
        },
        "_source": ["text", "metadata", "chunk_id", "doc_id"]
    }

    response = client.search(
        index=index_name,
        body=body,
        params={"search_pipeline": PIPELINE_ID}
    )

    feedback_index = _load_feedback_index()

    results = []
    for hit in response["hits"]["hits"]:
        base_score = hit["_score"] or 0.0
        metadata   = hit["_source"].get("metadata", {})
        chunk_id   = hit["_source"].get("chunk_id")

        # Factor de país: impulso si el documento pertenece al país de la consulta
        b_pais = COUNTRY_BOOST if (
            detected_country and
            metadata.get("pais", "").lower() == detected_country.lower()
        ) else 1.0

        # Factor de retroalimentación: impulso si el usuario lo calificó positivo
        b_feedback = FEEDBACK_BOOST if feedback_index.get(chunk_id) is True else 1.0

        results.append({
            "score":    base_score * b_pais * b_feedback,
            "text":     hit["_source"]["text"],
            "metadata": metadata,
            "chunk_id": chunk_id,
            "doc_id":   hit["_source"].get("doc_id")
        })

    # Ordenar por score final y devolver top_k
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


def format_context(results: List[Dict]) -> str:
    if not results:
        return "No se encontró información relevante."

    context_parts = []
    for i, r in enumerate(results, 1):
        meta = r["metadata"]
        header = f"[Fuente {i}]"
        if meta.get("title"):
            header += f" {meta['title']}"
        if meta.get("url"):
            header += f" ({meta['url']})"
        context_parts.append(f"{header}\n{r['text']}")

    return "\n\n---\n\n".join(context_parts)