from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any, Optional

from llm.ollama_client import generate

from retrival.domain_gating_policy import (
    DOMAIN_GATING_CONFIDENCE_THRESHOLD,
    DOMAIN_GATING_ENABLED,
    DOMAIN_GATING_MODEL,
    DOMAIN_GATING_TIMEOUT_SECONDS,
)


_SYSTEM_PROMPT = (
    "Eres un clasificador de dominio. "
    "Tu tarea es decidir si una consulta pertenece al dominio: turismo y viajes en Latinoamérica y el Caribe. "
    "El Caribe incluye: Cuba, Jamaica, Haití, República Dominicana, Puerto Rico, Bahamas, Barbados, "
    "Trinidad y Tobago, Aruba, Curazao, Santa Lucía, Granada, Dominica, Martinica, Guadalupe, "
    "San Vicente, Antigua, San Cristóbal y Nieves, Turcos y Caicos, Islas Caimán, entre otras. "
    "Responde estrictamente en formato JSON y sin texto extra."
)


def _build_prompt(query: str) -> str:
    q = (query or "").strip()
    return (
        "Devuelve SOLO un JSON con las siguientes claves y tipos:\n"
        "{\n"
        '  "in_domain": boolean,\n'
        '  "confidence": number,\n'
        '  "reason": string\n'
        "}\n\n"
        "Reglas:\n"
        "- in_domain=true si la consulta es sobre turismo/viajes en Latinoamérica o el Caribe (destinos, rutas, atracciones, cultura turística, recomendaciones, seguridad turística, transporte turístico, presupuesto de viaje). El Caribe completo es in_domain.\n"
        "- in_domain=false si el tema es ajeno (motores de avión, medicina, programación, deportes, ingeniería, etc.).\n"
        "- confidence debe estar entre 0 y 1.\n"
        "- reason debe ser una frase breve.\n\n"
        f"Consulta: {q}\n"
    )


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json_object(text: str) -> Optional[str]:
    if not text:
        return None
    m = _JSON_RE.search(text)
    return m.group(0) if m else None


def _clamp01(value: Any) -> Optional[float]:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f < 0:
        return 0.0
    if f > 1:
        return 1.0
    return f


def _normalize_response(payload: Any) -> dict:
    if not isinstance(payload, dict):
        return {
            "checked": True,
            "in_domain": True,
            "confidence": None,
            "reason": None,
        }

    in_domain = payload.get("in_domain")
    if not isinstance(in_domain, bool):
        in_domain = True

    confidence = _clamp01(payload.get("confidence"))
    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        reason = None

    # Si la confianza es muy baja, tratamos como fuera de dominio.
    # Esto evita que el modelo responda "sí" con poca certeza.
    if confidence is not None and confidence < DOMAIN_GATING_CONFIDENCE_THRESHOLD:
        in_domain = False

    return {
        "checked": True,
        "in_domain": bool(in_domain),
        "confidence": confidence,
        "reason": reason,
    }


@lru_cache(maxsize=256)
def classify_query_domain(query: str) -> dict:
    """Clasifica si una consulta pertenece al dominio de turismo en Latinoamérica.

    Política de errores: fail-open. Si ocurre un error, se considera `in_domain=True`
    para no bloquear el sistema.
    """
    if not DOMAIN_GATING_ENABLED:
        return {
            "checked": False,
            "in_domain": True,
            "confidence": None,
            "reason": None,
        }

    q = (query or "").strip()
    if not q:
        return {
            "checked": True,
            "in_domain": True,
            "confidence": None,
            "reason": None,
        }

    try:
        # Reusamos el cliente existente. El timeout se controla vía requests en ollama_client.
        # Se deja configurado aquí por claridad y futura extensión.
        _ = DOMAIN_GATING_TIMEOUT_SECONDS

        raw = generate(
            query=_build_prompt(q),
            context="",
            model=DOMAIN_GATING_MODEL,
            temperature=0.0,
            system_prompt=_SYSTEM_PROMPT,
        )

        json_str = _extract_json_object(raw) or raw
        payload = json.loads(json_str)
        return _normalize_response(payload)
    except Exception:
        return {
            "checked": True,
            "in_domain": True,
            "confidence": None,
            "reason": None,
        }
