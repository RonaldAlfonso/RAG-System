# RAG Turismo Latinoamérica

Sistema de preguntas y respuestas sobre turismo en Latinoamérica basado en RAG (Retrieval-Augmented Generation).

## Arquitectura

```
┌─────────────┐     POST /ask/stream      ┌─────────────────┐
│  Frontend   │ ─────────────────────────► │   API FastAPI   │
│ Vue3+Quasar │ ◄───────────────────────── │   :8000         │
└─────────────┘     SSE token stream       └────────┬────────┘
     :9000                                          │
                                          ┌─────────▼────────┐
                                          │  RAG Pipeline    │
                                          │  1. detect país  │
                                          │  2. hybrid search│
                                          │  3. LLM generate │
                                          └──┬───────────┬───┘
                                             │           │
                                   ┌─────────▼──┐  ┌─────▼──────┐
                                   │ OpenSearch │  │   Ollama   │
                                   │ KNN + BM25 │  │ qwen2.5:3b │
                                   │   :9200    │  │  nomic-emb │
                                   └────────────┘  └────────────┘
```

### Servicios

| Servicio | Descripción | Puerto |
|---|---|---|
| `frontend` | Interfaz de chat Vue 3 + Quasar | 9000 |
| `api` | API REST FastAPI con streaming SSE | 8000 |
| `ollama` | LLM (`qwen2.5:3b`) + embeddings (`nomic-embed-text`) | 11435 |
| `opensearch` | Vector DB con búsqueda híbrida KNN + BM25 | 9200 |
| `processor` | Servicio de indexado de documentos | — |
| `crawler` | Scraper de Wikivoyage | — |

---

## Requisitos previos

- **Docker** >= 24 y **Docker Compose** >= 2
- **Git**
- RAM: mínimo 6 GB disponibles
- Disco: ~5 GB (imágenes Docker + modelos LLM)

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repo> rag-proyect
cd rag-proyect
```

### 2. Crear el archivo `.env`

Crear un archivo `.env` en la raíz del proyecto con el siguiente contenido:

```env
# LLM
OLLAMA_URL=http://ollama:11434
LLM_MODEL=qwen2.5:3b

# Credenciales Backblaze B2
R2_ACCESS_KEY_ID=<tu_access_key>
R2_SECRET_ACCESS_KEY=<tu_secret_key>
R2_ENDPOINT_URL=https://s3.us-east-005.backblazeb2.com
R2_BUCKET_NAME=turismo-latam-raw
```

### 3. Levantar los servicios

```bash
docker compose up -d --build
```

La primera vez descarga las imágenes (~3–4 GB). Verificar que todo corra:

```bash
docker compose ps
```

Deben aparecer en estado `Up`: `opensearch`, `ollama`, `processor_rag`, `rag_api`, `rag_frontend`.

### 4. Descargar los modelos de Ollama

```bash
# Modelo de embeddings (384 MB)
docker exec ollama ollama pull nomic-embed-text

# Modelo LLM (2 GB)
docker exec ollama ollama pull qwen2.5:3b
```

Verificar que estén disponibles:

```bash
docker exec ollama ollama list
```

### 5. Crear el índice y el pipeline en OpenSearch

```bash
# Crear índice de documentos con soporte KNN
docker exec -it processor_rag python -c "
import sys; sys.path.insert(0, '/app/services')
from processor.vector_store import create_index
create_index()
print('Índice creado')
"

# Crear pipeline de búsqueda híbrida (KNN + BM25)
docker exec -it processor_rag python /app/services/retrival/search_pipeline.py
```

### 6. Indexar documentos

Descarga documentos desde Backblaze B2, los divide en chunks, genera embeddings y los indexa en OpenSearch:

```bash
docker exec -it processor_rag python /app/services/processor/main.py
```

> Puede tardar varios minutos dependiendo del volumen de documentos.

---

## Uso

Una vez completada la instalación, acceder a:

| URL | Descripción |
|---|---|
| http://localhost:9000 | Interfaz de chat |
| http://localhost:8000/docs | Swagger UI de la API |
| http://localhost:8000/health | Health check |

### Ejemplo de uso via API

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Qué playas hay en Colombia?", "top_k": 5}'
```

Respuesta con streaming SSE:

```bash
curl -X POST http://localhost:8000/ask/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Qué ver en Cusco, Perú?", "top_k": 5}'
```

### Probar el pipeline RAG desde consola

```bash
docker exec -it processor_rag python /app/services/retrival/rag_pipeline.py
```

---

## Estructura del proyecto

```
rag-proyect/
├── api/
│   └── main.py              # FastAPI: endpoints /ask y /ask/stream
├── frontend/
│   ├── src/
│   │   ├── composables/
│   │   │   └── useRag.ts    # Lógica de llamadas a la API + streaming
│   │   ├── pages/
│   │   │   └── IndexPage.vue # Interfaz de chat
│   │   └── router/
│   ├── quasar.config.js
│   └── tsconfig.json
├── services/
│   ├── llm/
│   │   └── ollama_client.py  # Cliente Ollama (generate + generate_stream)
│   ├── processor/
│   │   ├── chunker.py        # División de documentos en chunks
│   │   ├── embeddigns.py     # Generación de embeddings vía Ollama
│   │   ├── indexer.py        # Indexado en OpenSearch
│   │   ├── main.py           # Pipeline completo de procesamiento
│   │   └── vector_store.py   # Definición del índice OpenSearch
│   ├── retrival/
│   │   ├── country_detector.py  # Detección de país en la query
│   │   ├── rag_pipeline.py      # Pipeline RAG completo
│   │   ├── retriever.py         # Búsqueda híbrida KNN + BM25
│   │   └── search_pipeline.py   # Configuración del pipeline OpenSearch
│   └── scraper/
│       └── crawler.py        # Scraper Wikivoyage con Scrapy
├── .env                      # Variables de entorno (no versionado)
├── .dockerignore
├── docker-compose.yml
├── Dockerfile                # Imagen Python para api/processor/crawler
└── requirements.txt
```

---

## Comandos útiles

```bash
# Ver logs en tiempo real
docker compose logs -f api
docker compose logs -f frontend

# Reiniciar un servicio
docker compose restart api

# Detener todo
docker compose down

# Detener y eliminar volúmenes (borra datos de OpenSearch y modelos Ollama)
docker compose down -v
```

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `rag_frontend` tarda en arrancar | Instalando `node_modules` por primera vez | Esperar ~5 min: `docker compose logs -f frontend` |
| API devuelve `500` | OpenSearch u Ollama no listos | Esperar 30 s y reintentar |
| Respuestas sin información | Índice vacío | Ejecutar paso 6 |
| Error `model not found` | Modelo no descargado | Ejecutar paso 4 |
| OpenSearch no arranca | Poca memoria virtual | `sudo sysctl -w vm.max_map_count=262144` |
