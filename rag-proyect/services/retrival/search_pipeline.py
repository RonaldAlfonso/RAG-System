from processor.vector_store import client

def create_hybrid_pipeline(pipeline_id: str = "hybrid-pipeline"):
    """
    Crea un pipeline en OpenSearch que:
    1. Normaliza los scores de KNN y BM25 a la misma escala (0 a 1)
    2. Los combina con arithmetic_mean (promedio ponderado)
    """
    pipeline_body = {
        "description": "Pipeline para búsqueda híbrida KNN + BM25",
        "phase_results_processors": [
            {
                "normalization-processor": {
                    "normalization": {
                        "technique": "min_max"      # escala ambos scores entre 0 y 1
                    },
                    "combination": {
                        "technique": "arithmetic_mean",
                        "parameters": {
                            "weights": [0.2, 0.8]   # [BM25, KNN] — semántico pesa más
                        }
                    }
                }
            }
        ]
    }

    response = client.http.put(
        f"/_search/pipeline/{pipeline_id}",
        body=pipeline_body
    )
    print(f"✅ Pipeline '{pipeline_id}' creado: {response}")
    return response

if __name__ == "__main__":
    create_hybrid_pipeline()