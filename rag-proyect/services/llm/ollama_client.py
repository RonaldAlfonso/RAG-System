import os
import json
import requests
from typing import Optional, Generator

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")

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
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    system_prompt: Optional[str] = None,
) -> str:
    payload = {
        "model": model,
        "messages": _build_messages(query, context, system_prompt),
        "stream": False,
        "options": {"temperature": temperature},
    }
    response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120)
    response.raise_for_status()
    return response.json()["message"]["content"]


def generate_stream(
    query: str,
    context: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    system_prompt: Optional[str] = None,
) -> Generator[str, None, None]:
    payload = {
        "model": model,
        "messages": _build_messages(query, context, system_prompt),
        "stream": True,
        "options": {"temperature": temperature},
    }
    with requests.post(f"{OLLAMA_URL}/api/chat", json=payload,
                       stream=True, timeout=120) as response:
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
