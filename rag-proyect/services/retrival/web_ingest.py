from __future__ import annotations

from typing import Dict, List

from processor.chunker import chunk_documents


def ingest_web_documents(docs: List[dict]) -> Dict[str, int]:
    """Ingesta documentos web (texto + metadatos) en el índice de OpenSearch."""
    if not docs:
        return {"docs_received": 0, "chunks_indexed": 0}

    # Import diferido para soportar ejecución local sin dependencias de OpenSearch.
    from processor.indexer import BATCH_SIZE, WEB_CACHE_INDEX_NAME, index_chunks_batch

    all_chunks: List[dict] = []

    for doc in docs:
        metadata = doc.get("metadata", {})
        if metadata.get("pais") is None:
            metadata.pop("pais", None)
        doc["metadata"] = metadata

        chunks = chunk_documents(doc)

        for i, chunk in enumerate(chunks):
            chunk["chunk_index"] = i

        all_chunks.extend(chunks)

    if not all_chunks:
        return {"docs_received": len(docs), "chunks_indexed": 0}

    chunks_indexed = 0

    pending = list(all_chunks)
    while len(pending) >= BATCH_SIZE:
        batch = pending[:BATCH_SIZE]
        del pending[:BATCH_SIZE]
        indexed = index_chunks_batch(batch, index_name=WEB_CACHE_INDEX_NAME)
        chunks_indexed += int(indexed or 0)

    if pending:
        indexed = index_chunks_batch(pending, index_name=WEB_CACHE_INDEX_NAME)
        chunks_indexed += int(indexed or 0)

    return {"docs_received": len(docs), "chunks_indexed": chunks_indexed}
