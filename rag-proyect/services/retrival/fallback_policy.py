import os
from typing import Any, Iterable

# --- Inmutables (no cambiar) ---
OPENSEARCH_INDEX_NAME = "documents"
OPENSEARCH_PIPELINE_ID = "hybrid-pipeline"


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


# --- Variables de entorno (defaults en código) ---
WEB_FALLBACK_ENABLED: bool = _get_env_bool("WEB_FALLBACK_ENABLED", True)
WEB_FALLBACK_MAX_PAGES: int = _get_env_int("WEB_FALLBACK_MAX_PAGES", 3)
WEB_FALLBACK_TIMEOUT_SECONDS: int = _get_env_int("WEB_FALLBACK_TIMEOUT_SECONDS", 20)
WEB_FALLBACK_SCORE_THRESHOLD: float = _get_env_float("WEB_FALLBACK_SCORE_THRESHOLD", 0.6)
WEB_FALLBACK_CONTEXT_MIN_CHARS: int = _get_env_int("WEB_FALLBACK_CONTEXT_MIN_CHARS", 800)


def _safe_scores(results: Iterable[Any]) -> list[float]:
    """Extrae scores robustamente (esperamos dicts con key 'score')."""
    scores: list[float] = []
    for r in results or []:
        if isinstance(r, dict):
            s = r.get("score")
        else:
            s = getattr(r, "score", None)
        if s is None:
            continue
        try:
            scores.append(float(s))
        except (TypeError, ValueError):
            continue
    return scores


def is_insufficient(results: list[dict], context: str) -> bool:
    """Política única de “insuficiente información”.

    Insuficiente si se cumple cualquiera:
    - len(results) == 0
    - max(score) < WEB_FALLBACK_SCORE_THRESHOLD
    - len(context) < WEB_FALLBACK_CONTEXT_MIN_CHARS
    """
    if not results:
        return True

    scores = _safe_scores(results)
    # Si por algún motivo no hay scores parseables, tratamos como insuficiente.
    if not scores:
        return True

    if max(scores) < WEB_FALLBACK_SCORE_THRESHOLD:
        return True

    if context is None:
        return True

    if len(context) < WEB_FALLBACK_CONTEXT_MIN_CHARS:
        return True

    return False
