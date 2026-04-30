from opensearchpy import OpenSearch

client = OpenSearch(
    hosts=[{"host": "opensearch", "port": 9200}],
    http_compress=True,
    timeout=60
)

def create_index(index_name: str = "documents"):
    index_body = {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 100    # precisión en búsqueda KNN
            }
        },
        "mappings": {
            "properties": {
                # --- identidad ---
                "chunk_id": {
                    "type": "keyword"               # SHA-256 del texto; permite upsert
                },
                "doc_id": {
                    "type": "keyword"               # agrupa chunks del mismo documento
                },

                # --- búsqueda híbrida ---
                "text": {
                    "type": "text",                 # BM25 / full-text
                    "analyzer": "standard"
                },
                "text_keyword": {
                    "type": "keyword",              # filtros exactos
                    "ignore_above": 512
                },
                "embedding": {
                    "type": "knn_vector",
                    "dimension": 768,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil", # coseno = lo que espera nomic
                        "engine": "lucene",          # o "nmslib"; lucene no requiere plugin
                        "parameters": {
                            "m": 16,
                            "ef_construction": 128
                        }
                    }
                },

                # --- metadata estructurada ---
                "metadata": {
                    "type": "object",
                    "properties": {
                        "title":      {"type": "keyword"},
                        "url":        {"type": "keyword"},
                        "pais":       {"type": "keyword"},
                        "categoria":  {"type": "keyword"},
                        "chunk_index":{"type": "integer"},  # posición dentro del doc
                        "created_at": {"type": "date"}
                    }
                }
            }
        }
    }
    client.indices.create(index=index_name, body=index_body, ignore=400)