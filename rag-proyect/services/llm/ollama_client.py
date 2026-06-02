import os
import json
import requests
from typing import Optional, Generator

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL   = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
MISTRAL_URL     = "https://api.mistral.ai/v1/chat/completions"

# Fallback Ollama (solo si no hay API key de Mistral)
OLLAMA_URL    = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL  = os.getenv("LLM_MODEL", "qwen2.5:3b")

SYSTEM_PROMPT = """Eres un asistente experto en turismo de Latinoamérica.
Responde ÚNICAMENTE basándote en el contexto proporcionado.
Si la información no está en el contexto, indícalo claramente.
Escribe siempre en párrafos continuos. No uses listas, viñetas ni guiones.
Sé conciso, preciso y útil."""


def _build_messages(query: str, context: str, system_prompt: Optional[str]) -> list:
    system = system_prompt or SYSTEM_PROMPT
    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": f"Contexto:\n{context}\n\nPregunta: {query}"},
    ]


def generate(
    query: str,
    context: str,
    model: str = None,
    temperature: float = 0.3,
    system_prompt: Optional[str] = None,
) -> str:
    if MISTRAL_API_KEY:
        # Siempre usar MISTRAL_MODEL — ignorar model param para evitar
        # que nombres de modelos Ollama (ej. qwen2.5:3b) lleguen a la API de Mistral.
        return _mistral_generate(query, context, MISTRAL_MODEL, temperature, system_prompt)
    return _ollama_generate(query, context, model or OLLAMA_MODEL, temperature, system_prompt)


def generate_stream(
    query: str,
    context: str,
    model: str = None,
    temperature: float = 0.3,
    system_prompt: Optional[str] = None,
) -> Generator[str, None, None]:
    if MISTRAL_API_KEY:
        yield from _mistral_stream(query, context, MISTRAL_MODEL, temperature, system_prompt)
    else:
        yield from _ollama_stream(query, context, model or OLLAMA_MODEL, temperature, system_prompt)


# ── Mistral ────────────────────────────────────────────────────────────────────

def _mistral_headers() -> dict:
    return {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    }


def _mistral_generate(query, context, model, temperature, system_prompt) -> str:
    payload = {
        "model": model,
        "messages": _build_messages(query, context, system_prompt),
        "temperature": temperature,
        "stream": False,
    }
    response = requests.post(MISTRAL_URL, headers=_mistral_headers(), json=payload, timeout=60)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _mistral_stream(query, context, model, temperature, system_prompt) -> Generator[str, None, None]:
    payload = {
        "model": model,
        "messages": _build_messages(query, context, system_prompt),
        "temperature": temperature,
        "stream": True,
    }
    with requests.post(MISTRAL_URL, headers=_mistral_headers(), json=payload,
                       stream=True, timeout=60) as response:
        response.raise_for_status()
        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if line.startswith("data: "):
                line = line[6:]
            if line.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(line)
                token = chunk["choices"][0]["delta"].get("content", "")
                if token:
                    yield token
            except (json.JSONDecodeError, KeyError, IndexError):
                continue


# ── Ollama (fallback) ──────────────────────────────────────────────────────────

def _ollama_generate(query, context, model, temperature, system_prompt) -> str:
    payload = {
        "model": model,
        "messages": _build_messages(query, context, system_prompt),
        "stream": False,
        "options": {"temperature": temperature},
    }
    response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=300)
    response.raise_for_status()
    return response.json()["message"]["content"]


def _ollama_stream(query, context, model, temperature, system_prompt) -> Generator[str, None, None]:
    payload = {
        "model": model,
        "messages": _build_messages(query, context, system_prompt),
        "stream": True,
        "options": {"temperature": temperature},
    }
    with requests.post(f"{OLLAMA_URL}/api/chat", json=payload,
                       stream=True, timeout=300) as response:
        response.raise_for_status()
        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            chunk = json.loads(raw_line)
            token = chunk.get("message", {}).get("content", "")
            if token:
                yield token
            if chunk.get("done"):
                break
