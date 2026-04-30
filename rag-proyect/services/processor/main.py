from bucket_loader import BucketLoader
from chunker import chunk_documents
from processor.vector_store import create_index
from processor.indexer import index_chunks_batch, BATCH_SIZE

def process():
    create_index()
    loader = BucketLoader()
    print("🚀 Iniciando pipeline RAG\n")

    total_docs = 0
    total_chunks = 0
    pending_chunks = []   # buffer de chunks entre documentos

    def flush_pending():
        """Envía el buffer actual a Ollama + OpenSearch."""
        if pending_chunks:
            indexed = index_chunks_batch(pending_chunks)
            pending_chunks.clear()
            return indexed
        return 0

    for obj in loader.list_files():
        doc = loader.get_documents(obj)
        if not doc or not doc.get("text"):
            continue

        total_docs += 1
        chunks = chunk_documents(doc)

        # Añadir índice de posición a cada chunk
        for i, chunk in enumerate(chunks):
            chunk["chunk_index"] = i

        total_chunks += len(chunks)
        pending_chunks.extend(chunks)

        print(f"📄 {doc['metadata'].get('title', 'Sin título')}")
        print(f"   🔹 URL: {doc['metadata'].get('url')}")
        print(f"   ✂️  Chunks: {len(chunks)}")

        # Procesar en batches cuando acumulamos suficientes
        while len(pending_chunks) >= BATCH_SIZE:
            batch = pending_chunks[:BATCH_SIZE]
            del pending_chunks[:BATCH_SIZE]
            index_chunks_batch(batch)

    # Flush final (chunks que no llenaron el último batch)
    if pending_chunks:
        index_chunks_batch(pending_chunks)

    print("\n✅ PIPELINE TERMINADO")
    print(f"📊 Documentos: {total_docs} | Chunks: {total_chunks}")

if __name__ == "__main__":
    process()