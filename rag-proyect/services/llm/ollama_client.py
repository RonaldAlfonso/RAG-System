import os
import requests
from typing import Optional

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")

SYSTEM_PROMPT = """Eres un asistente experto en turismo de Latinoamérica.
Responde ÚNICAMENTE basándote en el contexto proporcionado.
Si la información no está en el contexto, indícalo claramente.
Sé conciso, preciso y útil."""


def generate(
    query: str,
    context: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    system_prompt: Optional[str] = None,
) -> str:
    system = system_prompt or SYSTEM_PROMPT
    user_message = f"""Contexto:
{context}

Pregunta: {query}"""

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_message},
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }

    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]
