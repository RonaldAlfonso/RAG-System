#!/usr/bin/env python3
"""
Script de evaluación del sistema RAG.
Ejecuta las consultas definidas en qrels.json y calcula métricas.

Uso desde la raíz del proyecto:
    python services/evaluation/run_evaluation.py

O desde services/:
    python evaluation/run_evaluation.py

Parámetros:
    --qrels        Ruta al archivo qrels.json  (default: evaluation/qrels.json)
    --top-k        Valores de k separados por comas  (default: 5,10,20)
    --use-fallback Activar el fallback web durante la evaluación
    --use-expansion Activar expansión de consultas y PRF
    --filters      Filtros JSON, ej. '{"pais": "Peru"}'
    --output-dir   Directorio donde guardar resultados  (default: evaluation/results)
"""

import sys
import os
import argparse
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.evaluator import load_qrels, run_queries
from evaluation.report_generator import (
    compute_metrics_for_result,
    aggregate_metrics,
    generate_report,
    to_text_table,
)


def main():
    parser = argparse.ArgumentParser(description="Evalúa el sistema RAG con un ground truth.")
    parser.add_argument('--qrels', type=str, default='evaluation/qrels.json',
                        help='Ruta al archivo qrels.json (por defecto: evaluation/qrels.json)')
    parser.add_argument('--top-k', type=str, default='5,10,20',
                        help='Lista de valores de k separados por comas (ej. 5,10,20)')
    parser.add_argument('--use-fallback', action='store_true',
                        help='Activar el fallback web durante la evaluación')
    parser.add_argument('--use-expansion', action='store_true',
                        help='Activar expansión de consultas y PRF')
    parser.add_argument('--filters', type=str, default=None,
                        help="Filtros en formato JSON (ej. '{\"pais\": \"Peru\"}')")
    parser.add_argument('--output-dir', type=str, default='evaluation/results',
                        help='Directorio donde guardar resultados intermedios')
    args = parser.parse_args()

    # Cargar ground truth
    if not os.path.exists(args.qrels):
        print(f"Error: No se encuentra el archivo {args.qrels}")
        print("Ejecute primero bootstrap_qrels.py para generar los juicios de relevancia.")
        sys.exit(1)

    qrels = load_qrels(args.qrels)
    annotated = [q for q in qrels if q.get('relevant_chunks')]
    print(f"Cargadas {len(qrels)} consultas ({len(annotated)} con juicios de relevancia).")

    if not annotated:
        print("No hay consultas con relevant_chunks poblados.")
        print("Ejecute primero: python evaluation/bootstrap_qrels.py")
        sys.exit(1)

    top_k_list = [int(k.strip()) for k in args.top_k.split(',')]
    filters = json.loads(args.filters) if args.filters else None

    # Ejecutar consultas
    results = run_queries(
        qrels=annotated,
        top_k_list=top_k_list,
        use_fallback=args.use_fallback,
        use_expansion=args.use_expansion,
        filters=filters,
        output_dir=args.output_dir
    )

    # Calcular métricas por consulta
    all_metrics = [compute_metrics_for_result(res, top_k_list) for res in results]

    # Agregar métricas
    aggregated = aggregate_metrics(all_metrics, top_k_list)

    # Generar informe (se guarda en evaluation/results/)
    report_path = generate_report(all_metrics, aggregated, top_k_list, output_dir=args.output_dir)
    print(f"\nInforme guardado en: {report_path}")

    # Mostrar resumen en consola
    print("\n=== RESUMEN ===\n")
    print(to_text_table(aggregated, top_k_list))


if __name__ == "__main__":
    main()