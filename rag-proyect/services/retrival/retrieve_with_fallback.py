from __future__ import annotations

from typing import Any, Dict, Optional

# Imports diferidos: permite importar este módulo en entornos sin dependencias de OpenSearch.


def retrieve_context_with_fallback(
    query: str,
    top_k: int,
    filters: Optional[dict] = None,
) -> Dict[str, Any]:
    """Recupera contexto con búsqueda híbrida y, si es insuficiente, intenta un fallback web.

    Retorna un diccionario con `results`, `context` y métricas del fallback.
    """
    from retrival.retriever import hybrid_search, format_context
    from retrival.web_fallback_wikivoyage import fetch_wikivoyage_pages
    from retrival.web_ingest import ingest_web_documents
    from retrival.domain_classifier import classify_query_domain
    from retrival.fallback_policy import (
        WEB_FALLBACK_ENABLED,
        WEB_FALLBACK_MAX_PAGES,
        WEB_FALLBACK_TIMEOUT_SECONDS,
        is_insufficient,
    )

    results_1 = hybrid_search(query, top_k=top_k, filters=filters)
    context_1 = format_context(results_1)
    insufficient = is_insufficient(results_1, context_1)

    if not WEB_FALLBACK_ENABLED:
        return {
            "results": results_1,
            "context": context_1,
            "web_fallback_attempted": False,
            "web_fallback_used": False,
            "web_docs_received": 0,
            "web_chunks_indexed": 0,
            "web_pages": [],
            "domain_gate_checked": False,
            "domain_gate_in_domain": True,
            "domain_gate_confidence": None,
            "domain_gate_reason": None,
        }

    if not insufficient:
        return {
            "results": results_1,
            "context": context_1,
            "web_fallback_attempted": False,
            "web_fallback_used": False,
            "web_docs_received": 0,
            "web_chunks_indexed": 0,
            "web_pages": [],
            "domain_gate_checked": False,
            "domain_gate_in_domain": True,
            "domain_gate_confidence": None,
            "domain_gate_reason": None,
        }

    domain = classify_query_domain(query)
    if domain.get("checked") and domain.get("in_domain") is False:
        return {
            "results": results_1,
            "context": context_1,
            "web_fallback_attempted": True,
            "web_fallback_used": False,
            "web_docs_received": 0,
            "web_chunks_indexed": 0,
            "web_pages": [],
            "domain_gate_checked": True,
            "domain_gate_in_domain": False,
            "domain_gate_confidence": domain.get("confidence"),
            "domain_gate_reason": domain.get("reason"),
        }

    docs = fetch_wikivoyage_pages(
        query,
        WEB_FALLBACK_MAX_PAGES,
        WEB_FALLBACK_TIMEOUT_SECONDS,
    )

    if not docs:
        return {
            "results": results_1,
            "context": context_1,
            "web_fallback_attempted": True,
            "web_fallback_used": False,
            "web_docs_received": 0,
            "web_chunks_indexed": 0,
            "web_pages": [],
            "domain_gate_checked": bool(domain.get("checked", False)),
            "domain_gate_in_domain": bool(domain.get("in_domain", True)),
            "domain_gate_confidence": domain.get("confidence"),
            "domain_gate_reason": domain.get("reason"),
        }

    stats = ingest_web_documents(docs)
    results_2 = hybrid_search(query, top_k=top_k, filters=filters)
    context_2 = format_context(results_2)

    return {
        "results": results_2,
        "context": context_2,
        "web_fallback_attempted": True,
        "web_fallback_used": True,
        "web_docs_received": int(stats.get("docs_received", 0) or 0),
        "web_chunks_indexed": int(stats.get("chunks_indexed", 0) or 0),
        "web_pages": [doc.get("metadata", {}) for doc in docs],
        "domain_gate_checked": bool(domain.get("checked", False)),
        "domain_gate_in_domain": bool(domain.get("in_domain", True)),
        "domain_gate_confidence": domain.get("confidence"),
        "domain_gate_reason": domain.get("reason"),
    }
