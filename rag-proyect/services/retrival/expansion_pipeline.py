from __future__ import annotations

from typing import List, Dict, Any, Tuple

from retrival.expansion_config import (
    EXPANSION_ENABLED,
    EXPAND_BEFORE_FIRST_SEARCH,
    PRF_AFTER_FIRST_SEARCH,
)
from retrival.query_expander_llm import expand_query_semantic
from retrival.pseudo_relevance_feedback import apply_pseudo_relevance_feedback

def apply_expansion_pipeline(
    original_query: str,
    first_search_results: List[Dict[str, Any]],
) -> Tuple[str, Dict[str, Any]]:
    stats = {
        "expansion_used": False,
        "prf_used": False,
        "original_query": original_query,
        "expanded_query_semantic": None,
        "prf_expanded_query": None,
    }

    if not EXPANSION_ENABLED:
        return original_query, stats

    current = original_query

    if EXPAND_BEFORE_FIRST_SEARCH:
        expanded = expand_query_semantic(current)
        if expanded != current:
            stats["expansion_used"] = True
            stats["expanded_query_semantic"] = expanded
            current = expanded

    if PRF_AFTER_FIRST_SEARCH and first_search_results:
        prf_query = apply_pseudo_relevance_feedback(current, first_search_results)
        if prf_query != current:
            stats["prf_used"] = True
            stats["prf_expanded_query"] = prf_query
            current = prf_query

    return current, stats