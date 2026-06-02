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
                                   ┌─────────▼──┐  ┌─────▼──────────────┐
                                   │ OpenSearch │  │  Ollama            │
                                   │ KNN + BM25 │  │  qwen2.5:3b (LLM)  │
                                   │   :9200    │  └────────────────────┘
                                   └────────────┘
                                                   ┌────────────────────┐
                                   Embeddings ───► │  Mistral API       │
                                   (indexado y     │  mistral-embed     │
                                    búsqueda)      │  (externo, HTTPS)  │
                                                   └────────────────────┘
```

### Servicios

| Servicio | Descripción | Puerto |
|---|---|---|
| `frontend` | Interfaz de chat Vue 3 + Quasar | 9000 |
| `api` | API REST FastAPI con streaming SSE | 8000 |
| `ollama` | LLM de generación (`qwen2.5:3b`) | 11435 |
| `opensearch` | Vector DB con búsqueda híbrida KNN + BM25 | 9200 |
| `processor` | Servicio de indexado de documentos | — |
| `crawler` | Scraper de contenido turístico | — |

> **Embeddings**: generados por la API externa de Mistral (`mistral-embed`, 1 024 dimensiones). No se usan embeddings locales de Ollama.

---

## Requisitos previos

- **Docker** >= 24 y **Docker Compose** >= 2
- **Git**
- **Cuenta en Mistral AI** con una API key (plan gratuito disponible en [console.mistral.ai](https://console.mistral.ai))
- RAM: mínimo 6 GB disponibles
- Disco: ~5 GB (imágenes Docker + modelo LLM)

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
# Mistral API (embeddings + modelo LLM alternativo)
MISTRAL_API_KEY=<tu_api_key_de_mistral>
MISTRAL_MODEL=mistral-small-latest

# Ollama (LLM local de generación)
OLLAMA_URL=http://ollama:11434
LLM_MODEL=qwen2.5:3b

# Credenciales Backblaze B2 (almacenamiento de documentos fuente)
R2_ACCESS_KEY_ID=<tu_access_key>
R2_SECRET_ACCESS_KEY=<tu_secret_key>
R2_ENDPOINT_URL=https://s3.us-east-005.backblazeb2.com
R2_BUCKET_NAME=turismo-latam-raw
```

> La `MISTRAL_API_KEY` es **obligatoria**: se usa para generar todos los embeddings durante la indexación y en cada búsqueda.

### 3. Levantar los servicios

```bash
docker compose up -d --build
```

La primera vez descarga las imágenes (~3–4 GB). Verificar que todo corra:

```bash
docker compose ps
```

Deben aparecer en estado `Up`: `opensearch`, `ollama`, `processor_rag`, `rag_api`, `rag_frontend`.

### 4. Descargar el modelo LLM en Ollama

Solo se necesita el modelo de generación de texto (los embeddings los provee Mistral API, no Ollama):

```bash
# Modelo LLM (~2 GB)
docker exec ollama ollama pull qwen2.5:3b
```

Verificar que esté disponible:

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

Descarga documentos desde Backblaze B2, los divide en chunks, genera embeddings con Mistral API y los indexa en OpenSearch:

```bash
docker exec -it processor_rag python /app/services/processor/main.py
```

> Puede tardar varios minutos. Cada batch de chunks hace una llamada a la API de Mistral.

#### Alternativa: indexar el volcado de Wikivoyage

Si no tienes documentos propios en B2, puedes poblar el índice directamente desde el dump de Wikivoyage en español:

```bash
docker exec -it processor_rag python /app/scripts/wikivoyage_dump_ingest.py
```

El script descarga el volcado XML comprimido, filtra artículos de América Latina y el Caribe, y los indexa automáticamente.

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
│   └── main.py                  # FastAPI: endpoints /ask y /ask/stream
├── frontend/
│   ├── src/
│   │   ├── composables/
│   │   │   └── useRag.ts        # Lógica de llamadas a la API + streaming
│   │   └── pages/
│   │       └── IndexPage.vue    # Interfaz de chat
│   └── quasar.config.js
├── scripts/
│   └── wikivoyage_dump_ingest.py  # Ingesta offline del dump de Wikivoyage
├── services/
│   ├── evaluation/
│   │   ├── evaluator.py         # Evaluación MAP/MRR/P@k/R@k/NDCG@k
│   │   ├── metrics.py           # Cálculo de métricas IR
│   │   ├── qrels.json           # Juicios de relevancia (30 consultas)
│   │   ├── run_evaluation.py    # Script principal de evaluación
│   │   └── results/             # Reportes y métricas generados
│   ├── llm/
│   │   └── ollama_client.py     # Cliente Ollama (generate + generate_stream)
│   ├── processor/
│   │   ├── chunker.py           # División de documentos en chunks
│   │   ├── embeddigns.py        # Embeddings vía Mistral API (mistral-embed)
│   │   ├── indexer.py           # Indexado en OpenSearch
│   │   ├── main.py              # Pipeline completo de procesamiento
│   │   └── vector_store.py      # Definición del índice OpenSearch (HNSW)
│   └── retrival/
│       ├── country_detector.py      # Detección de país en la consulta
│       ├── domain_classifier.py     # Clasificador de dominio vía LLM
│       ├── expansion_pipeline.py    # Expansión de consultas (LLM + PRF)
│       ├── pseudo_relevance_feedback.py
│       ├── query_expander_llm.py
│       ├── rag_pipeline.py          # Pipeline RAG completo
│       ├── reranker.py              # Reordenamiento con cross-encoder
│       ├── retriever.py             # Búsqueda híbrida KNN + BM25
│       ├── retrieve_with_fallback.py # Recuperación con fallback web
│       ├── search_pipeline.py       # Configuración del pipeline OpenSearch
│       └── web_fallback_wikivoyage.py # Fallback automático a Wikivoyage
├── .env                         # Variables de entorno (no versionado)
├── docker-compose.yml
├── Dockerfile
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

# Ejecutar evaluación completa de los 5 modos del pipeline
docker exec -it processor_rag python /app/services/evaluation/run_evaluation.py
```

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `RuntimeError: MISTRAL_API_KEY no está configurada` | Falta la variable en `.env` | Agregar `MISTRAL_API_KEY` al `.env` y reiniciar con `docker compose up -d` |
| `rag_frontend` tarda en arrancar | Instalando `node_modules` por primera vez | Esperar ~5 min: `docker compose logs -f frontend` |
| API devuelve `500` | OpenSearch u Ollama no listos | Esperar 30 s y reintentar |
| Respuestas sin información | Índice vacío | Ejecutar paso 6 |
| Error `model not found` | Modelo LLM no descargado | Ejecutar paso 4 |
| OpenSearch no arranca | Poca memoria virtual | `sudo sysctl -w vm.max_map_count=262144` |
