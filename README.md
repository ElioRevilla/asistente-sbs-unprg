# Asistente Educativo SBS

Backend y frontend inicial para una PWA educativa sobre la Resolucion SBS N. 11356-2008. Incluye FastAPI, Clean Architecture, configuracion por entorno, migraciones SQL crudas, ingesta inicial hacia PostgreSQL con pgvector y una interfaz React para los modos `Explicame` y `Ejemplifica`.

## Requisitos

- Python 3.12
- uv
- Node.js 22+

## Setup local

```bash
uv sync
```

En Windows, si PowerShell no reconoce `uv`, usar primero:

```powershell
py -m uv sync --all-groups
```

Despues de sincronizar y activar `.venv`, tambien deberia funcionar:

```powershell
uv sync --all-groups
uv run pytest
```

Copiar `.env.example` a `.env` y completar valores cuando toque conectar servicios de GCP. Para este incremento, los defaults locales son suficientes para correr la API y las pruebas.

## Ejecutar API

```bash
uv run uvicorn sbs_assistant.api.main:app --reload
```

Healthcheck:

```bash
curl http://127.0.0.1:8000/health
```

Respuesta esperada:

```json
{
  "status": "ok",
  "service": "sbs-assistant",
  "environment": "local"
}
```

## Ejecutar frontend

La app web vive en `frontend/` y usa Firebase Authentication con email/password.

Instalar dependencias y levantar Vite:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Abrir:

```text
http://127.0.0.1:5173
```

El frontend llama al backend en `http://127.0.0.1:8000` por defecto. Para permitir CORS en local, `.env` del backend debe incluir:

```env
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

Configura `frontend/.env` con los datos de tu app web Firebase:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=sbs-assistant-unprg.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=sbs-assistant-unprg
VITE_FIREBASE_APP_ID=
```

En Firebase Console habilita Authentication con proveedor email/password y crea usuarios de prueba. El backend valida el ID token de Firebase cuando llega en el header `Authorization: Bearer <token>`.

Para exigir token en todos los endpoints protegidos, activa en `.env` del backend:

```env
FIREBASE_AUTH_REQUIRED=true
FIREBASE_PROJECT_ID=sbs-assistant-unprg
```

## Validacion

```bash
uv run pytest
uv run ruff check .
uv run black --check .
```

Validar frontend:

```powershell
cd frontend
npm.cmd run build
```

## Despliegue en Cloud Run

El despliegue productivo usa GitHub Actions, Artifact Registry, Workload Identity Federation y dos servicios de Cloud Run:

- `sbs-assistant-api`
- `sbs-assistant-web`

La guía completa está en:

```text
docs/deployment_cloud_run.md
```

## Migraciones SQL

Las migraciones viven en `db/migrations` y se ejecutan en orden lexicografico.

```bash
uv run python scripts/setup_postgres.py
```

El script requiere credenciales de PostgreSQL por variables de entorno. No se ejecuta en las pruebas unitarias.

## Ingesta del PDF SBS

El script de ingesta descarga el PDF real definido en `SBS_PDF_URL`, lo parsea en chunks por articulo y escribe en PostgreSQL las tablas `chunks` y `provision_rules`.

Primero completa en `.env`:

```env
GCP_PROJECT_ID=sbs-assistant-unprg
CLOUDSQL_INSTANCE=sbs-postgres
DB_NAME=sbs_assistant
DB_USER=postgres
DB_PASSWORD=
```

Ejecutar migraciones:

```powershell
uv run python scripts/setup_postgres.py
```

Ingesta real a base de datos, sin embeddings ni GCS:

```powershell
uv run python scripts/ingest_sbs_pdf.py --skip-gcs
```

Si el sitio de SBS devuelve una pagina anti-bot en vez del PDF, descarga el PDF manualmente con el navegador y ejecuta:

```powershell
uv run python scripts/ingest_sbs_pdf.py --pdf-path .\ruta\al\archivo.pdf --skip-gcs
```

Ingesta con subida del PDF original a Cloud Storage:

```powershell
uv run python scripts/ingest_sbs_pdf.py
```

Para generar embeddings reales con Vertex AI:

```powershell
uv run python scripts/ingest_sbs_pdf.py --with-embeddings
```

Ese modo requiere `GCP_PROJECT_ID`, `VERTEX_AI_LOCATION`, `EMBEDDINGS_MODEL` y credenciales de Google disponibles en el entorno.

## Embeddings y busqueda RAG

Si los chunks ya fueron cargados sin embeddings, puedes poblar solo la columna `chunks.embedding` sin reingestar el PDF:

```powershell
uv run python scripts/embed_chunks.py
```

Para regenerar todos los embeddings:

```powershell
uv run python scripts/embed_chunks.py --all
```

Probar recuperacion hibrida sobre PostgreSQL:

```powershell
uv run python scripts/search_chunks.py "que es categoria deficiente"
uv run python scripts/search_chunks.py "provision para garantia preferida" --top-k 3 --tema provisiones
```

El buscador combina pgvector, full text search en espanol y Reciprocal Rank Fusion.

## Modo Explícame

Endpoint inicial del primer modo pedagogico:

```http
POST /modes/explain
```

Body:

```json
{
  "question": "Que es categoria deficiente?",
  "top_k": 3
}
```

Respuesta:

```json
{
  "type": "text",
  "data": {
    "answer": "...",
    "citations": [
      {
        "chunk_id": "sec_029_3_3",
        "label": "Numeral 3.3",
        "text_preview": "..."
      }
    ]
  }
}
```

Este modo usa el retriever hibrido, Gemini Flash y un prompt restrictivo en
espanol LATAM con citacion obligatoria.
