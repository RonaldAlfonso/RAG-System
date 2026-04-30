import requests
from typing import List

OLLAMA_URL = "http://ollama:11434/api/embed"  # endpoint batch (Ollama ≥0.1.34)

def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Llama a Ollama una sola vez para N textos.
    El endpoint /api/embed acepta lista en 'input' (plural).
    """
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "nomic-embed-text",
            "input": texts          # lista, no string
        },
        timeout=120
    )
    response.raise_for_status()
    return response.json()["embeddings"]  # lista de vectores

def get_embedding(text: str) -> List[float]:
    """Wrapper de un solo texto (útil para búsqueda)."""
    return get_embeddings_batch([text])[0]