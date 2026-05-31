from __future__ import annotations

from typing import List, Set, Dict, Any
import numpy as np

def precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Precisión@k: (número de relevantes en top-k) / k
    """
    if k <= 0:
        return 0.0
    retrieved_at_k = retrieved[:k]
    relevant_at_k = sum(1 for doc in retrieved_at_k if doc in relevant)
    return relevant_at_k / k

def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Recall@k: (número de relevantes en top-k) / |relevantes totales|
    """
    if not relevant:
        return 0.0
    retrieved_at_k = retrieved[:k]
    relevant_at_k = sum(1 for doc in retrieved_at_k if doc in relevant)
    return relevant_at_k / len(relevant)

def f1_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    F1@k: media armónica de precision@k y recall@k
    """
    p = precision_at_k(retrieved, relevant, k)
    r = recall_at_k(retrieved, relevant, k)
    if p + r == 0:
        return 0.0
    return 2 * (p * r) / (p + r)

def average_precision(retrieved: List[str], relevant: Set[str]) -> float:
    """
    Precisión media (AP): promedio de precision@k para cada posición donde aparece un relevante.
    """
    if not relevant:
        return 0.0
    ap_sum = 0.0
    num_relevant_found = 0
    for i, doc in enumerate(retrieved, start=1):
        if doc in relevant:
            num_relevant_found += 1
            ap_sum += num_relevant_found / i
    return ap_sum / len(relevant)

def mean_average_precision(results_list: List[Dict[str, Any]]) -> float:
    """
    MAP: media de AP sobre todas las consultas.
    results_list: lista de dict con claves 'retrieved' y 'relevant'
    """
    if not results_list:
        return 0.0
    aps = [average_precision(r['retrieved'], r['relevant']) for r in results_list]
    return float(np.mean(aps))

def reciprocal_rank(retrieved: List[str], relevant: Set[str]) -> float:
    """
    Reciprocal Rank (RR): 1 / (posición del primer relevante). 0 si no hay relevante.
    """
    for i, doc in enumerate(retrieved, start=1):
        if doc in relevant:
            return 1.0 / i
    return 0.0

def mean_reciprocal_rank(results_list: List[Dict[str, Any]]) -> float:
    """
    MRR: media de RR sobre todas las consultas.
    """
    if not results_list:
        return 0.0
    rrs = [reciprocal_rank(r['retrieved'], r['relevant']) for r in results_list]
    return float(np.mean(rrs))

def ndcg_at_k(retrieved: List[str], relevant: Set[str], k: int, gain_scheme: str = 'binary') -> float:
    """
    NDCG@k: Normalized Discounted Cumulative Gain.
    gain_scheme: 'binary' → 1 si es relevante, 0 en caso contrario.
    """
    if k <= 0:
        return 0.0
    # Ideal ranking: todos los relevantes al principio
    ideal = [1] * len(relevant) + [0] * (k - len(relevant))
    ideal_dcg = _dcg(ideal, k)

    gains = [1 if doc in relevant else 0 for doc in retrieved[:k]]
    dcg = _dcg(gains, k)

    if ideal_dcg == 0:
        return 0.0
    return dcg / ideal_dcg

def _dcg(gains: List[float], k: int) -> float:
    """Calcula DCG@k.

    Fórmula estándar: DCG@k = sum_{i=1}^{k} rel_i / log2(i+1).
    Con enumerate desde 0, la posición i (0-indexed) corresponde a log2(i+2).
    """
    dcg = 0.0
    for i, g in enumerate(gains[:k]):
        dcg += g / np.log2(i + 2)
    return dcg