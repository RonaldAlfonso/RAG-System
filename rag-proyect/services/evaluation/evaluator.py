from __future__ import annotations

import json
import os
from typing import List, Dict, Any, Set, Optional
import sys

# Asegurar que se pueda importar desde servicios
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retrival.retriever import hybrid_search
from retrival.retrieve_with_fallback import retrieve_context_with_fallback
from retrival.fallback_policy import WEB_FALLBACK_ENABLED, is_insufficient


def load_qrels(qrels_path: str) -> List[Dict[str, Any]]:
    """Carga el archivo qrels.json con las consultas y chunks relevantes."""
    with open(qrels_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Se espera una lista de objetos con 'query_id', 'query_text', 'relevant_chunks'
    if isinstance(data, dict) and 'queries' in data:
        return data['queries']
    if isinstance(data, list):
        return data
    raise ValueError("Formato de qrels no soportado. Use lista o {'queries': [...]}")


def run_queries(
    qrels: List[Dict[str, Any]],
    top_k_list: List[int] = [5, 10, 20],
    use_fallback: bool = False,
    use_expansion: bool = False,
    filters: Optional[Dict] = None,
    output_dir: str = "evaluation/results"
) -> List[Dict[str, Any]]:
    """
    Ejecuta las consultas del ground truth y guarda los ranked lists.
    Retorna una lista de resultados por consulta con 'retrieved' (listas de chunk_id para cada k).

    Modos de búsqueda:
    - use_fallback=True : retrieve_context_with_fallback (incluye expansión + fallback web)
    - use_expansion=True, use_fallback=False : hybrid_search con query expandida por LLM
    - ambos False (baseline): hybrid_search directo sin expansión
    """
    os.makedirs(output_dir, exist_ok=True)


    results = []
    for q in qrels:
        query_text = q['query_text']
        relevant_set = set(q['relevant_chunks'])
        query_id = q.get('query_id', len(results))

        print(f"Ejecutando consulta {query_id}: {query_text[:50]}...")

        if use_fallback:
            # retrieve_context_with_fallback ya incluye expansión + fallback web
            retrieval = retrieve_context_with_fallback(
                query=query_text,
                top_k=max(top_k_list),
                filters=filters
            )
            retrieved_docs = retrieval['results']
        elif use_expansion:
            # Expansión semántica explícita (sin fallback web)
            from retrival.expansion_pipeline import apply_expansion_pipeline
            expanded_query, _ = apply_expansion_pipeline(query_text, [])
            retrieved_docs = hybrid_search(
                query=expanded_query,
                top_k=max(top_k_list),
                filters=filters
            )
        else:
            # Baseline: búsqueda directa sin expansión ni fallback
            retrieved_docs = hybrid_search(
                query=query_text,
                top_k=max(top_k_list),
                filters=filters
            )

        # Extraer chunk_ids en orden
        chunk_ids = [doc.get('chunk_id', doc.get('_id', '')) for doc in retrieved_docs if doc.get('chunk_id')]

        # Guardar para cada k
        ranked_by_k = {}
        for k in top_k_list:
            ranked_by_k[f'retrieved_{k}'] = chunk_ids[:k]

        result_entry = {
            'query_id': query_id,
            'query_text': query_text,
            'relevant': list(relevant_set),
            **ranked_by_k,
            'full_ranking': chunk_ids
        }
        results.append(result_entry)

    # Guardar resultados intermedios
    out_file = os.path.join(output_dir, 'ranked_lists.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return results