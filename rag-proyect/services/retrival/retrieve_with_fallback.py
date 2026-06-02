from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from retrival.expansion_pipeline import apply_expansion_pipeline

log = logging.getLogger(__name__)


def _log_expansion(original: str, stats: dict, final_query: str) -> None:
    sep = "─" * 60
    log.info(sep)
    log.info("QUERY ORIGINAL   : %s", original)
    if stats.get("expansion_used"):
        log.info("EXPANSIÓN LLM    : %s", stats.get("expanded_query_semantic"))
    else:
        log.info("EXPANSIÓN LLM    : (no aplicada)")
    if stats.get("prf_used"):
        log.info("PRF              : %s", stats.get("prf_expanded_query"))
    else:
        log.info("PRF              : (no aplicado)")
    if stats.get("expansion_used") or stats.get("prf_used"):
        log.info("QUERY FINAL      : %s", final_query)
    log.info(sep)


def retrieve_context_with_fallback(
    query: str,
    top_k: int,
    filters: Optional[dict] = None,
) -> Dict[str, Any]:
    """Recupera contexto con búsqueda en tres niveles:
      1. KB principal  (índice 'documents')
      2. KB web cache  (índice 'web_cache', datos de Wikivoyage ya indexados)
      3. Fallback web  (busca en Wikivoyage, ingesta en 'web_cache', re-busca)
    """
    from retrival.retriever import hybrid_search, format_context, WEB_CACHE_INDEX_NAME
    from retrival.web_fallback_wikivoyage import fetch_wikivoyage_pages
    from retrival.web_ingest import ingest_web_documents
    from retrival.domain_classifier import classify_query_domain
    from retrival.fallback_policy import (
        WEB_FALLBACK_ENABLED,
        WEB_FALLBACK_MAX_PAGES,
        WEB_FALLBACK_TIMEOUT_SECONDS,
        is_insufficient,
    )

    def _base_return(results, context, **extra):
        return {
            "results": results,
            "context": context,
            "web_cache_used": False,
            "web_fallback_attempted": False,
            "web_fallback_used": False,
            "web_docs_received": 0,
            "web_chunks_indexed": 0,
            "web_pages": [],
            "domain_gate_checked": False,
            "domain_gate_in_domain": True,
            "domain_gate_confidence": None,
            "domain_gate_reason": None,
            "expansion_used": False,
            "prf_used": False,
            "original_query": query,
            "expanded_query_semantic": None,
            "prf_expanded_query": None,
            **extra,
        }

    # ── Nivel 1: KB principal ────────────────────────────────────────────────
    results_1 = hybrid_search(query, top_k=top_k, filters=filters)
    context_1 = format_context(results_1)

    expansion_stats: dict = {}

    if not is_insufficient(results_1, context_1):
        expanded_query, expansion_stats = apply_expansion_pipeline(query, results_1)
        _log_expansion(query, expansion_stats, expanded_query)
        if expansion_stats.get("expansion_used") or expansion_stats.get("prf_used"):
            results_2 = hybrid_search(expanded_query, top_k=top_k, filters=filters)
            context_2 = format_context(results_2)
            return _base_return(
                results_2, context_2,
                expansion_used=expansion_stats.get("expansion_used", False),
                prf_used=expansion_stats.get("prf_used", False),
                original_query=expansion_stats.get("original_query", query),
                expanded_query_semantic=expansion_stats.get("expanded_query_semantic"),
                prf_expanded_query=expansion_stats.get("prf_expanded_query"),
            )
        return _base_return(results_1, context_1)

    # Resultados insuficientes en KB principal
    if not WEB_FALLBACK_ENABLED:
        return _base_return(results_1, context_1)

    # ── Nivel 2: KB web cache ────────────────────────────────────────────────
    cache_results = hybrid_search(query, top_k=top_k, filters=filters,
                                  index_name=WEB_CACHE_INDEX_NAME)
    cache_context = format_context(cache_results)

    if not is_insufficient(cache_results, cache_context):
        return _base_return(cache_results, cache_context, web_cache_used=True)

    # ── Nivel 3: Fallback web → ingesta en web_cache → re-busca ─────────────
    domain = classify_query_domain(query)
    if domain.get("checked") and domain.get("in_domain") is False:
        return _base_return(
            results_1, context_1,
            web_fallback_attempted=True,
            domain_gate_checked=True,
            domain_gate_in_domain=False,
            domain_gate_confidence=domain.get("confidence"),
            domain_gate_reason=domain.get("reason"),
        )

    docs = fetch_wikivoyage_pages(query, WEB_FALLBACK_MAX_PAGES, WEB_FALLBACK_TIMEOUT_SECONDS)
    if not docs:
        return _base_return(
            results_1, context_1,
            web_fallback_attempted=True,
            domain_gate_checked=bool(domain.get("checked", False)),
            domain_gate_in_domain=bool(domain.get("in_domain", True)),
            domain_gate_confidence=domain.get("confidence"),
            domain_gate_reason=domain.get("reason"),
        )

    stats = ingest_web_documents(docs)

    results_final = hybrid_search(query, top_k=top_k, filters=filters,
                                  index_name=WEB_CACHE_INDEX_NAME)
    context_final = format_context(results_final)

    return _base_return(
        results_final, context_final,
        web_cache_used=True,
        web_fallback_attempted=True,
        web_fallback_used=True,
        web_docs_received=int(stats.get("docs_received", 0) or 0),
        web_chunks_indexed=int(stats.get("chunks_indexed", 0) or 0),
        web_pages=[doc.get("metadata", {}) for doc in docs],
        domain_gate_checked=bool(domain.get("checked", False)),
        domain_gate_in_domain=bool(domain.get("in_domain", True)),
        domain_gate_confidence=domain.get("confidence"),
        domain_gate_reason=domain.get("reason"),
    )
