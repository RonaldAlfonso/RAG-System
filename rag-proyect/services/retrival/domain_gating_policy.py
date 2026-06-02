import os


def _get_env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = raw.strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def _get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_env_str(name: str, default: str) -> str:
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = raw.strip()
    return raw or default


"""Configuración del gating por dominio.

Estas variables controlan si se permite ejecutar el fallback web según si la
consulta pertenece al dominio de turismo en Latinoamérica.
"""

DOMAIN_GATING_ENABLED: bool = _get_env_bool("DOMAIN_GATING_ENABLED", True)
DOMAIN_GATING_MODEL: str = _get_env_str("DOMAIN_GATING_MODEL", os.getenv("MISTRAL_MODEL") or os.getenv("LLM_MODEL", ""))
DOMAIN_GATING_CONFIDENCE_THRESHOLD: float = _get_env_float(
    "DOMAIN_GATING_CONFIDENCE_THRESHOLD", 0.7
)
DOMAIN_GATING_TIMEOUT_SECONDS: int = _get_env_int("DOMAIN_GATING_TIMEOUT_SECONDS", 15)
