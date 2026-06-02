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

# ── Activación general ────────────────────────────────────────────────────────
EXPANSION_ENABLED: bool = _get_env_bool("EXPANSION_ENABLED", True)

# ── Expansión semántica con LLM ───────────────────────────────────────────────
SEMANTIC_EXPANSION_ENABLED: bool = _get_env_bool("SEMANTIC_EXPANSION_ENABLED", True)
SEMANTIC_EXPANSION_MODEL: str = _get_env_str("SEMANTIC_EXPANSION_MODEL", os.getenv("MISTRAL_MODEL") or os.getenv("LLM_MODEL", "qwen2.5:3b"))
SEMANTIC_EXPANSION_TERMS: int = _get_env_int("SEMANTIC_EXPANSION_TERMS", 5)
SEMANTIC_EXPANSION_TEMPERATURE: float = _get_env_float("SEMANTIC_EXPANSION_TEMPERATURE", 0.4)

# ── Pseudo‑relevance feedback ─────────────────────────────────────────────────
PRF_ENABLED: bool = _get_env_bool("PRF_ENABLED", True)
PRF_TOP_K_DOCS: int = _get_env_int("PRF_TOP_K_DOCS", 5)
PRF_TOP_N_TERMS: int = _get_env_int("PRF_TOP_N_TERMS", 10)
PRF_MIN_TERM_LEN: int = _get_env_int("PRF_MIN_TERM_LEN", 3)
PRF_STOPWORDS_LANG: str = _get_env_str("PRF_STOPWORDS_LANG", "spanish")

# ── Comportamiento combinado ──────────────────────────────────────────────────
EXPAND_BEFORE_FIRST_SEARCH: bool = _get_env_bool("EXPAND_BEFORE_FIRST_SEARCH", True)
PRF_AFTER_FIRST_SEARCH: bool = _get_env_bool("PRF_AFTER_FIRST_SEARCH", True)