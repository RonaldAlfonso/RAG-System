from __future__ import annotations

import os
from typing import List, Dict, Any

RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        _model = CrossEncoder(RERANKER_MODEL)
    return _model


def rerank(query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Re-ordena resultados usando un cross-encoder. Preserva todos los campos originales."""
    if not results:
        return results

    model = _get_model()
    pairs = [(query, r["text"]) for r in results]
    scores = model.predict(pairs)

    ranked = sorted(zip(scores, results), key=lambda x: x[0], reverse=True)

    reranked = []
    for score, doc in ranked:
        doc = dict(doc)
        doc["rerank_score"] = float(score)
        reranked.append(doc)

    return reranked
