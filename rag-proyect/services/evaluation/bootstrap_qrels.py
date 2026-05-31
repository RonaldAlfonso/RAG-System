#!/usr/bin/env python3
"""
bootstrap_qrels.py — Pobla qrels.json con juicios de relevancia reales.

Para cada consulta sin relevant_chunks, ejecuta hybrid_search(top_k=20) y
usa el LLM como juez de relevancia (LLM-as-judge) para decidir qué chunks
son realmente relevantes para la consulta.

Los resultados se guardan incrementalmente en qrels.json para que el script
pueda retomarse en caso de interrupción.

Uso:
    # Desde services/:
    python evaluation/bootstrap_qrels.py

    # Con opciones:
    python evaluation/bootstrap_qrels.py --top-k 20 --qrels evaluation/qrels.json
"""

import sys
import os
import argparse
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retrival.retriever import hybrid_search
from llm.ollama_client import generate

JUDGE_SYSTEM_PROMPT = (
    "Eres un evaluador de relevancia para un sistema de recuperación de información "
    "sobre turismo en Latinoamérica. Tu tarea es decidir si un fragmento de texto "
    "es relevante para responder una consulta dada. "
    "Responde ÚNICAMENTE con 'sí' o 'no', sin explicaciones."
)


def _build_judge_prompt(query: str, chunk_text: str) -> str:
    return (
        f"Consulta: \"{query}\"\n\n"
        f"Fragmento de texto:\n{chunk_text[:600]}\n\n"
        "¿Este fragmento contiene información útil y directamente relevante "
        "para responder la consulta anterior? Responde solo 'sí' o 'no'."
    )


def judge_relevance(query: str, chunk_text: str, model: str) -> bool:
    """Usa el LLM para decidir si un chunk es relevante para la query."""
    prompt = _build_judge_prompt(query, chunk_text)
    try:
        response = generate(
            query=prompt,
            context="",
            model=model,
            temperature=0.0,
            system_prompt=JUDGE_SYSTEM_PROMPT,
        )
        answer = response.strip().lower()
        return answer.startswith("sí") or answer.startswith("si")
    except Exception as e:
        print(f"      ⚠️  Error en LLM judge: {e}")
        return False


def bootstrap(
    qrels_path: str,
    top_k: int,
    model: str,
    delay_seconds: float,
    force: bool,
) -> None:
    """
    Para cada consulta en qrels_path con relevant_chunks vacío (o force=True),
    busca top_k chunks y los anota con el LLM.
    """
    with open(qrels_path, "r", encoding="utf-8") as f:
        qrels = json.load(f)

    total = len(qrels)
    annotated_count = sum(1 for q in qrels if q.get("relevant_chunks"))
    print(f"Cargadas {total} consultas ({annotated_count} ya anotadas).\n")

    for i, q in enumerate(qrels):
        query_id = q.get("query_id", i)
        query_text = q["query_text"]
        existing = q.get("relevant_chunks", [])

        if existing and not force:
            print(f"[{query_id:02d}/{total}] Ya anotada — {query_text[:50]} ({len(existing)} chunks)")
            continue

        print(f"[{query_id:02d}/{total}] Anotando: {query_text}")

        # Recuperar candidatos del índice
        try:
            results = hybrid_search(query=query_text, top_k=top_k)
        except Exception as e:
            print(f"      ⚠️  Error en búsqueda: {e}. Saltando.")
            continue

        if not results:
            print(f"      Sin resultados en el índice para esta consulta.")
            continue

        relevant_chunks = []
        for j, r in enumerate(results):
            chunk_id = r.get("chunk_id")
            text = r.get("text", "")
            if not chunk_id or not text:
                continue

            is_rel = judge_relevance(query_text, text, model)
            label = "✓ relevante" if is_rel else "✗ no relevante"
            print(f"      chunk {j+1:02d}/{len(results)}: {label} — {text[:60].replace(chr(10), ' ')}")

            if is_rel:
                relevant_chunks.append(chunk_id)

            # Pausa entre llamadas al LLM para no saturar Ollama
            if delay_seconds > 0:
                time.sleep(delay_seconds)

        q["relevant_chunks"] = relevant_chunks
        print(f"      → {len(relevant_chunks)} chunks relevantes marcados.\n")

        # Guardar progreso incremental después de cada consulta
        with open(qrels_path, "w", encoding="utf-8") as f:
            json.dump(qrels, f, indent=2, ensure_ascii=False)

    annotated_final = sum(1 for q in qrels if q.get("relevant_chunks"))
    print(f"\n✅ Bootstrap completado. {annotated_final}/{total} consultas con juicios de relevancia.")
    print(f"Archivo actualizado: {qrels_path}")


def main() -> None:
    default_model = os.getenv("LLM_MODEL", "qwen2.5:3b")
    default_qrels = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrels.json")

    parser = argparse.ArgumentParser(
        description="Pobla qrels.json con juicios de relevancia usando el LLM como juez."
    )
    parser.add_argument(
        "--qrels", type=str, default=default_qrels,
        help=f"Ruta al archivo qrels.json (default: {default_qrels})"
    )
    parser.add_argument(
        "--top-k", type=int, default=20,
        help="Número de chunks candidatos a evaluar por consulta (default: 20)"
    )
    parser.add_argument(
        "--model", type=str, default=default_model,
        help=f"Modelo Ollama a usar como juez (default: {default_model})"
    )
    parser.add_argument(
        "--delay", type=float, default=0.5,
        help="Pausa en segundos entre llamadas al LLM (default: 0.5)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-anotar consultas que ya tienen relevant_chunks"
    )
    args = parser.parse_args()

    if not os.path.exists(args.qrels):
        print(f"Error: No se encuentra {args.qrels}")
        sys.exit(1)

    bootstrap(
        qrels_path=args.qrels,
        top_k=args.top_k,
        model=args.model,
        delay_seconds=args.delay,
        force=args.force,
    )


if __name__ == "__main__":
    main()
