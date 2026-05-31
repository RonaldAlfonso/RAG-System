from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import List, Optional

from llm.ollama_client import generate
from retrival.expansion_config import (
    SEMANTIC_EXPANSION_ENABLED,
    SEMANTIC_EXPANSION_MODEL,
    SEMANTIC_EXPANSION_TERMS,
    SEMANTIC_EXPANSION_TEMPERATURE,
)

_SYSTEM_PROMPT = (
    "Eres un asistente especializado en turismo de Latinoamérica. "
    "Genera términos o frases cortas relacionadas con la consulta del usuario."
)

def _build_prompt(query: str, num_terms: int) -> str:
    return (
        f"Genera exactamente {num_terms} términos o frases cortas (máximo 3 palabras cada una) "
        f"relacionadas con turismo en Latinoamérica para la siguiente consulta:\n\n"
        f"Consulta: {query}\n\n"
        "Devuelve ÚNICAMENTE una lista en formato JSON, sin texto adicional, como:\n"
        '["término1", "término2", ...]'
    )

def _parse_json_list(raw: str) -> Optional[List[str]]:
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        if isinstance(data, list):
            return [str(t).strip(' "\'') for t in data if str(t).strip()]
    except json.JSONDecodeError:
        return None
    return None

@lru_cache(maxsize=256)
def expand_query_semantic(query: str) -> str:
    if not SEMANTIC_EXPANSION_ENABLED:
        return query
    if not query or not query.strip():
        return query

    prompt = _build_prompt(query, SEMANTIC_EXPANSION_TERMS)
    try:
        raw = generate(
            query=prompt,
            context="",
            model=SEMANTIC_EXPANSION_MODEL,
            temperature=SEMANTIC_EXPANSION_TEMPERATURE,
            system_prompt=_SYSTEM_PROMPT,
        )
        terms = _parse_json_list(raw)
        if terms:
            return (query + " " + " ".join(terms)).strip()
    except Exception:
        pass
    return query