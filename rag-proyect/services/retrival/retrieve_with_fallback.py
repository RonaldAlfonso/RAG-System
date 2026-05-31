from __future__ import annotations

from typing import Any, Dict, Optional

from retrival.expansion_pipeline import apply_expansion_pipeline


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

    # Primera búsqueda (query original, sin expansión)
    results_1 = hybrid_search(query, top_k=top_k, filters=filters)
    context_1 = format_context(results_1)

    expansion_stats = {}
    final_results = results_1
    final_context = context_1

    expanded_query, exp_stats = apply_expansion_pipeline(query, results_1)
    if exp_stats.get("expansion_used") or exp_stats.get("prf_used"):
        results_2 = hybrid_search(expanded_query, top_k=top_k, filters=filters)
        context_2 = format_context(results_2)
        final_results = results_2
        final_context = context_2
        expansion_stats = exp_stats

    # Evaluar insuficiencia con los mejores resultados disponibles (post-expansión)
    insufficient = is_insufficient(final_results, final_context)

    # Si el fallback está deshabilitado, retornar lo que tengamos
    if not WEB_FALLBACK_ENABLED:
        return {
            "results": final_results,
            "context": final_context,
            "web_fallback_attempted": False,
            "web_fallback_used": False,
            "web_docs_received": 0,
            "web_chunks_indexed": 0,
            "web_pages": [],
            "domain_gate_checked": False,
            "domain_gate_in_domain": True,
            "domain_gate_confidence": None,
            "domain_gate_reason": None,
            "expansion_used": expansion_stats.get("expansion_used", False),
            "prf_used": expansion_stats.get("prf_used", False),
            "original_query": expansion_stats.get("original_query", query),
            "expanded_query_semantic": expansion_stats.get("expanded_query_semantic"),
            "prf_expanded_query": expansion_stats.get("prf_expanded_query"),
        }

    if not insufficient:
        return {
            "results": final_results,
            "context": final_context,
            "web_fallback_attempted": False,
            "web_fallback_used": False,
            "web_docs_received": 0,
            "web_chunks_indexed": 0,
            "web_pages": [],
            "domain_gate_checked": False,
            "domain_gate_in_domain": True,
            "domain_gate_confidence": None,
            "domain_gate_reason": None,
            "expansion_used": expansion_stats.get("expansion_used", False),
            "prf_used": expansion_stats.get("prf_used", False),
            "original_query": expansion_stats.get("original_query", query),
            "expanded_query_semantic": expansion_stats.get("expanded_query_semantic"),
            "prf_expanded_query": expansion_stats.get("prf_expanded_query"),
        }

    # Clasificador de dominio (solo si vamos a hacer fallback)
    domain = classify_query_domain(query)
    if domain.get("checked") and domain.get("in_domain") is False:
        return {
            "results": final_results,
            "context": final_context,
            "web_fallback_attempted": True,
            "web_fallback_used": False,
            "web_docs_received": 0,
            "web_chunks_indexed": 0,
            "web_pages": [],
            "domain_gate_checked": True,
            "domain_gate_in_domain": False,
            "domain_gate_confidence": domain.get("confidence"),
            "domain_gate_reason": domain.get("reason"),
            "expansion_used": expansion_stats.get("expansion_used", False),
            "prf_used": expansion_stats.get("prf_used", False),
            "original_query": expansion_stats.get("original_query", query),
            "expanded_query_semantic": expansion_stats.get("expanded_query_semantic"),
            "prf_expanded_query": expansion_stats.get("prf_expanded_query"),
        }

    # Fallback web
    docs = fetch_wikivoyage_pages(query, WEB_FALLBACK_MAX_PAGES, WEB_FALLBACK_TIMEOUT_SECONDS)
    if not docs:
        return {
            "results": final_results,
            "context": final_context,
            "web_fallback_attempted": True,
            "web_fallback_used": False,
            "web_docs_received": 0,
            "web_chunks_indexed": 0,
            "web_pages": [],
            "domain_gate_checked": bool(domain.get("checked", False)),
            "domain_gate_in_domain": bool(domain.get("in_domain", True)),
            "domain_gate_confidence": domain.get("confidence"),
            "domain_gate_reason": domain.get("reason"),
            "expansion_used": expansion_stats.get("expansion_used", False),
            "prf_used": expansion_stats.get("prf_used", False),
            "original_query": expansion_stats.get("original_query", query),
            "expanded_query_semantic": expansion_stats.get("expanded_query_semantic"),
            "prf_expanded_query": expansion_stats.get("prf_expanded_query"),
        }

    stats = ingest_web_documents(docs)
    results_final = hybrid_search(query, top_k=top_k, filters=filters)
    context_final = format_context(results_final)

    return {
        "results": results_final,
        "context": context_final,
        "web_fallback_attempted": True,
        "web_fallback_used": True,
        "web_docs_received": int(stats.get("docs_received", 0) or 0),
        "web_chunks_indexed": int(stats.get("chunks_indexed", 0) or 0),
        "web_pages": [doc.get("metadata", {}) for doc in docs],
        "domain_gate_checked": bool(domain.get("checked", False)),
        "domain_gate_in_domain": bool(domain.get("in_domain", True)),
        "domain_gate_confidence": domain.get("confidence"),
        "domain_gate_reason": domain.get("reason"),
        "expansion_used": expansion_stats.get("expansion_used", False),
        "prf_used": expansion_stats.get("prf_used", False),
        "original_query": expansion_stats.get("original_query", query),
        "expanded_query_semantic": expansion_stats.get("expanded_query_semantic"),
        "prf_expanded_query": expansion_stats.get("prf_expanded_query"),
    }
