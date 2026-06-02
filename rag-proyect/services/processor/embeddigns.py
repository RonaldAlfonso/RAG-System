import os
import requests
from typing import List

MISTRAL_API_KEY     = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_EMBED_URL   = "https://api.mistral.ai/v1/embeddings"
MISTRAL_EMBED_MODEL = "mistral-embed"


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    if not MISTRAL_API_KEY:
        raise RuntimeError(
            "MISTRAL_API_KEY no está configurada. "
            "Agrégala al .env y reinicia los contenedores."
        )
    response = requests.post(
        MISTRAL_EMBED_URL,
        headers={
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": MISTRAL_EMBED_MODEL, "input": texts},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()["data"]
    return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]


def get_embedding(text: str) -> List[float]:
    return get_embeddings_batch([text])[0]
