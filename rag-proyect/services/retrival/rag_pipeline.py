import sys
sys.path.insert(0, "/app/services")

from retrival.retriever import hybrid_search, format_context
from retrival.country_detector import detect_country
from llm.ollama_client import generate


def ask(query: str, top_k: int = 5, filters: dict = None) -> dict:
    detected_country = detect_country(query)

    active_filters = dict(filters) if filters else {}
    if detected_country and "pais" not in active_filters:
        active_filters["pais"] = detected_country

    results = hybrid_search(query, top_k=top_k, filters=active_filters or None)
    context = format_context(results)
    answer = generate(query=query, context=context)

    return {
        "query":            query,
        "answer":           answer,
        "sources":          results,
        "context":          context,
        "detected_country": detected_country,
        "filters_applied":  active_filters,
    }


if __name__ == "__main__":
    query = input("Pregunta: ").strip() or "¿Qué lugares turísticos hay en Cusco?"

    print(f"\n🔍 Buscando contexto para: {query}\n")
    response = ask(query)

    if response["detected_country"]:
        print(f"🌎 País detectado: {response['detected_country']} — filtro aplicado\n")

    print("=" * 60)
    print(f"🤖 Respuesta:\n\n{response['answer']}")
    print("=" * 60)
    print(f"\n📚 Fuentes usadas ({len(response['sources'])}):")
    for i, s in enumerate(response["sources"], 1):
        title = s["metadata"].get("title", "Sin título")
        url   = s["metadata"].get("url", "")
        score = s["score"]
        print(f"  {i}. [{score:.4f}] {title} {url}")
