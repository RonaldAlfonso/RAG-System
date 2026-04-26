from bucket_loader import BucketLoader
from chunker import chunk_documents


def process():
    loader = BucketLoader()

    print("🚀 Iniciando pipeline RAG (bucket → chunking por párrafos)\n")

    total_docs = 0
    total_chunks = 0

    # ─────────────────────────────────────────────
    # STREAMING REAL DE ARCHIVOS
    # ─────────────────────────────────────────────
    for obj in loader.iter_all_files():

        doc = loader.get_document(obj)

        if not doc:
            continue

        if not doc["text"]:
            continue

        total_docs += 1

        # ─────────────────────────────────────────
        #  CHUNKING POR PÁRRAFOS
        # ─────────────────────────────────────────
        chunks = chunk_document(doc)

        total_chunks += len(chunks)

        print(f"--- {doc['metadata'].get('title', 'Sin título')}")
        print(f"   -- URL: {doc['metadata'].get('url')}")
        print(f"   -- País: {doc['metadata'].get('pais', 'N/A')}")
        print(f"   -- Categoría: {doc['metadata'].get('categoria', 'N/A')}")
        print(f"   - Chunks generados: {len(chunks)}")

        # ejemplo de chunk para debug
        if chunks:
            print(f"    Sample chunk: {chunks[0]['text'][:120]}...\n")

        # ─────────────────────────────────────────
        #  AQUÍ IRÁ EMBEDDING + VECTOR DB
        # ─────────────────────────────────────────
        # embed_and_store(chunks)

    print("\n PIPELINE TERMINADO")
    print(f" Documentos procesados: {total_docs}")
    print(f" Total chunks generados: {total_chunks}")


if __name__ == "__main__":
    process()