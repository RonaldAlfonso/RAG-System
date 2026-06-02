from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Set

from .metrics import (
    precision_at_k, recall_at_k, f1_at_k, average_precision,
    reciprocal_rank, ndcg_at_k
)


def compute_metrics_for_result(
    result: Dict[str, Any],
    top_k_list: List[int]
) -> Dict[str, Any]:
    """
    Calcula todas las métricas para una consulta.
    """
    relevant = set(result['relevant'])
    retrieved_full = result['full_ranking']
    metrics = {
        'query_id': result['query_id'],
        'query_text': result['query_text'],
        'ap': average_precision(retrieved_full, relevant),
        'rr': reciprocal_rank(retrieved_full, relevant),
    }
    for k in top_k_list:
        retrieved_k = result.get(f'retrieved_{k}', retrieved_full[:k])
        metrics[f'p@{k}'] = precision_at_k(retrieved_k, relevant, k)
        metrics[f'r@{k}'] = recall_at_k(retrieved_k, relevant, k)
        metrics[f'f1@{k}'] = f1_at_k(retrieved_k, relevant, k)
        metrics[f'ndcg@{k}'] = ndcg_at_k(retrieved_k, relevant, k)
    return metrics


def aggregate_metrics(all_metrics: List[Dict[str, Any]], top_k_list: List[int]) -> Dict[str, Any]:
    """
    Promedia las métricas sobre todas las consultas.
    """
    agg: Dict[str, List[float]] = {}
    for k in top_k_list:
        agg[f'p@{k}'] = []
        agg[f'r@{k}'] = []
        agg[f'f1@{k}'] = []
        agg[f'ndcg@{k}'] = []
    agg['ap'] = []
    agg['mrr'] = []

    for m in all_metrics:
        agg['ap'].append(m['ap'])
        agg['mrr'].append(m['rr'])
        for k in top_k_list:
            agg[f'p@{k}'].append(m[f'p@{k}'])
            agg[f'r@{k}'].append(m[f'r@{k}'])
            agg[f'f1@{k}'].append(m[f'f1@{k}'])
            agg[f'ndcg@{k}'].append(m[f'ndcg@{k}'])

    aggregated: Dict[str, Dict[str, float]] = {}
    for key, values in agg.items():
        n = len(values)
        mean_val = sum(values) / n if n > 0 else 0.0
        std_val = (sum((x - mean_val) ** 2 for x in values) / n) ** 0.5 if n > 1 else 0.0
        aggregated[key] = {'mean': mean_val, 'std': std_val}

    return aggregated


def to_text_table(aggregated: Dict[str, Any], top_k_list: List[int]) -> str:
    """
    Genera una tabla en formato texto/markdown.
    """
    lines = []
    lines.append("## Resultados de evaluación del sistema RAG\n")
    lines.append("| Métrica | Media | Desv. estándar |")
    lines.append("|---------|-------|----------------|")
    for k in top_k_list:
        lines.append(f"| Precisión@{k} | {aggregated[f'p@{k}']['mean']:.4f} | {aggregated[f'p@{k}']['std']:.4f} |")
        lines.append(f"| Recall@{k} | {aggregated[f'r@{k}']['mean']:.4f} | {aggregated[f'r@{k}']['std']:.4f} |")
        lines.append(f"| F1@{k} | {aggregated[f'f1@{k}']['mean']:.4f} | {aggregated[f'f1@{k}']['std']:.4f} |")
        lines.append(f"| NDCG@{k} | {aggregated[f'ndcg@{k}']['mean']:.4f} | {aggregated[f'ndcg@{k}']['std']:.4f} |")
    lines.append(f"| MAP | {aggregated['ap']['mean']:.4f} | {aggregated['ap']['std']:.4f} |")
    lines.append(f"| MRR | {aggregated['mrr']['mean']:.4f} | {aggregated['mrr']['std']:.4f} |")
    return "\n".join(lines)


def to_json(aggregated: Dict[str, Any]) -> str:
    """Devuelve el JSON con las métricas agregadas."""
    return json.dumps(aggregated, indent=2)


def generate_report(
    all_metrics: List[Dict[str, Any]],
    aggregated: Dict[str, Any],
    top_k_list: List[int],
    mode: str = "baseline",
    output_dir: str = "evaluation/reports"
) -> str:
    """
    Genera un informe completo y lo guarda en un archivo con timestamp y modo.
    Retorna la ruta del archivo generado.
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(output_dir, f"report_{mode}_{timestamp}.txt")
    json_path = os.path.join(output_dir, f"metrics_{mode}_{timestamp}.json")

    # Guardar métricas detalladas por consulta
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_metrics, f, indent=2, ensure_ascii=False)

    # Generar informe texto
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=== INFORME DE EVALUACIÓN DEL SISTEMA RAG ===\n")
        f.write(f"Modo: {mode}\n")
        f.write(f"Fecha: {datetime.now().isoformat()}\n\n")
        f.write(to_text_table(aggregated, top_k_list))
        f.write("\n\n=== Métricas detalladas por consulta ===\n")
        for m in all_metrics:
            f.write(f"\nConsulta {m['query_id']}: {m['query_text']}\n")
            f.write(f"  AP: {m['ap']:.4f}, RR: {m['rr']:.4f}\n")
            for k in top_k_list:
                f.write(f"  P@{k}: {m[f'p@{k}']:.4f}, R@{k}: {m[f'r@{k}']:.4f}, F1@{k}: {m[f'f1@{k}']:.4f}, NDCG@{k}: {m[f'ndcg@{k}']:.4f}\n")

    return report_path