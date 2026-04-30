from typing import List, Dict, Optional
from processor.vector_store import client
from processor.embeddigns import get_embedding

INDEX_NAME = "documents"
PIPELINE_ID = "hybrid-pipeline"

def hybrid_search(
    query: str,
    top_k: int = 5,
    filters: Optional[Dict] = None
) -> List[Dict]:
    query_vector = get_embedding(query)

    # hybrid query siempre va en el top level, nunca dentro de bool
    body = {
        "size": top_k,
        "query": {
            "hybrid": {
                "queries": [
                    {
                        "match": {
                            "text": {
                                "query": query
                            }
                        }
                    },
                    {
                        "knn": {
                            "embedding": {
                                "vector": query_vector,
                                "k": top_k
                            }
                        }
                    }
                ]
            }
        },
        "_source": ["text", "metadata", "chunk_id", "doc_id"]
    }

    # los filtros van en post_filter, se aplican DESPUÉS de la búsqueda híbrida
    if filters:
        body["post_filter"] = {
            "bool": {
                "must": [
                    {"term": {f"metadata.{key}": value}}
                    for key, value in filters.items()
                ]
            }
        }

    response = client.search(
        index=INDEX_NAME,
        body=body,
        params={"search_pipeline": PIPELINE_ID}
    )

    results = []
    for hit in response["hits"]["hits"]:
        results.append({
            "score":    hit["_score"],
            "text":     hit["_source"]["text"],
            "metadata": hit["_source"].get("metadata", {}),
            "chunk_id": hit["_source"].get("chunk_id"),
            "doc_id":   hit["_source"].get("doc_id")
        })

    return results


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