import sys
sys.path.insert(0, "/app/services")

from retrival.retriever import hybrid_search, format_context
from retrival.search_pipeline import create_hybrid_pipeline

def test():
    # Crear el pipeline (solo la primera vez)
    create_hybrid_pipeline()

    # Prueba de búsqueda simple
    query = "¿Qué lugares turísticos hay en Cusco?"
    print(f"\n🔍 Query: {query}\n")

    results = hybrid_search(query, top_k=5)

    print(f"📊 {len(results)} resultados encontrados:\n")
    for i, r in enumerate(results, 1):
        print(f"  {i}. Score: {r['score']:.4f}")
        print(f"     País: {r['metadata'].get('pais', 'N/A')}")
        print(f"     Título: {r['metadata'].get('title', 'N/A')}")
        print(f"     Texto: {r['text'][:150]}...\n")

    # Prueba con filtro por país
    print("\n🌎 Búsqueda con filtro por país (Peru):\n")
    results_filtrados = hybrid_search(
        query="playas y turismo",
        top_k=3,
        filters={"pais": "Peru"}
    )
    for r in results_filtrados:
        print(f"  - {r['metadata'].get('title')} | Score: {r['score']:.4f}")

    # Ver contexto formateado para el LLM
    print("\n📝 Contexto para el LLM:\n")
    print(format_context(results[:3]))

if __name__ == "__main__":
    test()