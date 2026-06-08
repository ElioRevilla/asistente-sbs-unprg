# Asistente Educativo SBS

Aplicacion educativa sobre la Resolucion SBS N. 11356-2008 para estudiantes universitarios. El proyecto combina un backend FastAPI con arquitectura limpia, PostgreSQL/pgvector en Cloud SQL, Vertex AI para embeddings y Gemini, Firebase Authentication y un frontend React/Vite desplegable en Cloud Run.

## Estado Actual

- Backend FastAPI con modos `Explicame` y `Ejemplifica`.
- RAG hibrido con PostgreSQL, pgvector, full text search en espanol y RRF.
- Ingesta del PDF SBS con `pypdf`, chunking por secciones y embeddings Vertex AI.
- Reglas de provision y FCC cargadas desde seeds curados.
- Modo `Ejemplifica` con casos auditables, variacion narrativa opcional y practica adaptativa por estudiante.
- Frontend React con login Firebase, historial persistido y chat unico con selector de modo.
- Evaluacion offline con dataset de 20 preguntas de validacion.
- CI/CD con GitHub Actions hacia dos servicios de Cloud Run.

## Estructura del Proyecto

```text
.
|-- .github/
|   `-- workflows/
|       |-- ci.yml
|       `-- deploy.yml
|-- data/
|   |-- fcc_rules_seed.csv
|   `-- provision_rules_seed.csv
|-- db/
|   `-- migrations/
|       |-- 001_initial_schema.sql
|       |-- 002_create_fcc_rules.sql
|       |-- 003_create_chat_conversations.sql
|       |-- 004_create_example_mastery.sql
|       `-- 005_create_simulation_sessions.sql
|-- docs/
|   |-- deployment_cloud_run.md
|   `-- table_inventory.md
|-- frontend/
|   |-- index.html
|   |-- src/
|   |   |-- app/
|   |   |   |-- App.tsx
|   |   |   `-- Dashboard.tsx
|   |   |-- features/
|   |   |   |-- auth/
|   |   |   |   |-- LoginPage.tsx
|   |   |   |   `-- authStore.ts
|   |   |   `-- chat/
|   |   |       `-- AssistantChat.tsx
|   |   |-- services/
|   |   |   |-- apiClient.ts
|   |   |   `-- firebase.ts
|   |   |-- shared/
|   |   |   |-- apiTypes.ts
|   |   |   `-- markdown.tsx
|   |   |-- main.tsx
|   |   |-- vite-env.d.ts
|   |   `-- styles.css
|   |-- Dockerfile
|   |-- nginx.conf
|   |-- package-lock.json
|   |-- package.json
|   |-- tsconfig.json
|   |-- tsconfig.node.json
|   `-- vite.config.ts
|-- sbs_assistant/
|   |-- api/
|   |   |-- auth/
|   |   |   `-- firebase.py
|   |   |-- routes/
|   |   |   |-- chat_history.py
|   |   |   |-- example.py
|   |   |   |-- explain.py
|   |   |   `-- health.py
|   |   |-- schemas/
|   |   |   |-- request_schemas.py
|   |   |   `-- response_schemas.py
|   |   `-- main.py
|   |-- application/
|   |   |-- prompts/
|   |   |   `-- explain.py
|   |   |-- services/
|   |   |   |-- adaptive_example_policy.py
|   |   |   |-- example_case_templates.py
|   |   |   |-- llm_example_variation.py
|   |   |   `-- retrieval_planner.py
|   |   `-- use_cases/
|   |       |-- calculate_provision.py
|   |       |-- explain_concept.py
|   |       |-- generate_example.py
|   |       |-- ingest_document.py
|   |       `-- validate_example_answer.py
|   |-- config/
|   |   `-- settings.py
|   |-- domain/
|   |   |-- entities/
|   |   |-- ports/
|   |   `-- value_objects/
|   `-- infrastructure/
|       |-- embeddings/
|       |   |-- null_embeddings.py
|       |   `-- vertex_embeddings.py
|       |-- llm/
|       |   `-- vertex_gemini_client.py
|       |-- parsing/
|       |   |-- pypdf_document_parser.py
|       |   `-- sbs_text_chunker.py
|       |-- persistence/
|       |   |-- connection.py
|       |   |-- postgres_chat_history_repo.py
|       |   |-- postgres_chunk_repo.py
|       |   |-- postgres_example_mastery_repo.py
|       |   |-- postgres_provision_rule_repo.py
|       |   `-- postgres_synthetic_case_repo.py
|       |-- retrieval/
|       |   `-- postgres_hybrid_retriever.py
|       `-- storage/
|           |-- gcs_storage.py
|           |-- http_pdf_storage.py
|           `-- local_pdf_storage.py
|-- scripts/
|   |-- check_ingestion_counts.py
|   |-- embed_chunks.py
|   |-- ingest_sbs_pdf.py
|   |-- search_chunks.py
|   |-- seed_fcc_rules.py
|   |-- seed_provision_rules.py
|   |-- setup_postgres.py
|   `-- setup_postgres_migrations.py
|-- tests/
|   |-- eval/
|   |   |-- __init__.py
|   |   |-- run_eval.py
|   |   `-- sbs_validation_questions.json
|   |-- integration/
|   |   `-- __init__.py
|   `-- unit/
|       |-- test_example_api.py
|       |-- test_explain_api.py
|       |-- test_generate_example.py
|       |-- test_health.py
|       `-- ...
|-- .dockerignore
|-- .env.example
|-- .gitignore
|-- AGENTS.md
|-- Dockerfile
|-- pyproject.toml
`-- uv.lock
```

## Capas Principales

### Backend

- `sbs_assistant/domain`: entidades, value objects y ports. No debe depender de FastAPI, PostgreSQL, Vertex AI ni Firebase.
- `sbs_assistant/application`: casos de uso y servicios de aplicacion. Contiene la logica pedagogica, planificacion de retrieval y calculos deterministas.
- `sbs_assistant/application/services/adaptive_example_policy.py`: selecciona el siguiente caso adaptativo y produce recomendaciones pedagogicas.
- `sbs_assistant/infrastructure`: adaptadores concretos para PostgreSQL, Cloud SQL, Vertex AI, Gemini, GCS, parsing del PDF y retrieval hibrido.
- `sbs_assistant/infrastructure/persistence/postgres_example_mastery_repo.py`: persiste dominio por estudiante y concepto en `example_mastery`.
- `sbs_assistant/api`: app FastAPI, rutas HTTP, schemas y autenticacion Firebase.
- `sbs_assistant/config`: settings con Pydantic Settings y variables de entorno.

### Frontend

- `frontend/src/features/auth`: login Firebase y estado de sesion.
- `frontend/src/features/chat`: interfaz principal tipo chat con selector `Explicame` / `Ejemplifica`, practica adaptativa y bloqueo de casos pendientes sin validar.
- `frontend/src/services`: cliente HTTP y configuracion Firebase.
- `frontend/src/shared`: tipos compartidos y renderizado de markdown con reparacion de mojibake para historial antiguo.

### Datos y Despliegue

- `db/migrations`: SQL crudo versionado para Cloud SQL PostgreSQL.
- `data`: seeds curados para reglas de provision y factores de conversion crediticia.
- `scripts`: utilidades de setup, ingesta, embeddings, busqueda y seeds.
- `docs`: documentacion operativa, despliegue y validacion de tablas.
- `.github/workflows`: CI y despliegue a Cloud Run.

## Requisitos

- Python 3.12+
- uv
- Node.js 22+
- Google Cloud SDK
- Cuenta Firebase/GCP configurada para produccion

## Setup Local

Instalar dependencias Python:

```powershell
uv sync --all-groups
```

Copiar variables base:

```powershell
Copy-Item .env.example .env
```

Completar `.env` con las credenciales locales necesarias. No commitear `.env`.

## Ejecutar Backend

```powershell
uv run uvicorn sbs_assistant.api.main:app --reload
```

Alternativa si el entorno ya tiene dependencias instaladas:

```powershell
python -m uvicorn sbs_assistant.api.main:app --reload
```

Healthcheck:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Respuesta esperada:

```json
{
  "status": "ok",
  "service": "sbs-assistant",
  "environment": "local"
}
```

## Ejecutar Frontend

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Abrir:

```text
http://127.0.0.1:5173
```

Configurar `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=sbs-assistant-unprg.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=sbs-assistant-unprg
VITE_FIREBASE_APP_ID=
```

Para CORS local, el `.env` del backend debe incluir:

```env
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

## Endpoints Implementados

```http
GET  /health
POST /modes/explain
POST /modes/example/generate
POST /modes/example/answer
POST /modes/simulation/start
POST /modes/simulation/{session_id}/classify
POST /modes/simulation/{session_id}/turn
GET  /modes/simulation/{session_id}
GET  /chat/conversations
PUT  /chat/conversations/{conversation_id}
DELETE /chat/conversations/{conversation_id}
```

`/modes/explain` usa retrieval hibrido, Gemini Flash y citas obligatorias.

`/modes/example/*` genera y valida casos sinteticos auditables. La variacion narrativa con Gemini es opcional y solo modifica campos seguros.

En `Ejemplifica`, si `adaptive=true`, el backend:

- identifica el concepto evaluado por el caso,
- actualiza `example_mastery` cuando el estudiante valida su respuesta,
- baja o sube dominio con una regla deterministica,
- propone el siguiente foco pedagogico,
- rota variantes auditables para evitar repetir exactamente el mismo caso.

El frontend no genera otro caso si hay uno pendiente sin validar; primero pide seleccionar categoria y validar.

`/modes/simulation/*` expone la simulacion adversarial: el alumno clasifica
una operacion, responde objeciones del Supervisor y recibe veredicto al cierre.
La verdad de fondo del caso no se serializa al cliente hasta que la sesion queda
en estado `CLOSED`.

## Base de Datos y Migraciones

Las migraciones viven en `db/migrations` y se ejecutan en orden lexicografico.

```text
001_initial_schema.sql
002_create_fcc_rules.sql
003_create_chat_conversations.sql
004_create_example_mastery.sql
005_create_simulation_sessions.sql
```

Ejecutar migraciones:

```powershell
uv run python scripts/setup_postgres.py
```

El proyecto usa Cloud SQL PostgreSQL 16 con `pgvector`. La decision actual es no usar AlloyDB para el MVP por costo.

## Ingesta del PDF SBS

El PDF fuente puede estar localmente en:

```text
data/20160719_res-11356-2008.pdf
```

Ingesta desde archivo local sin GCS:

```powershell
uv run python scripts/ingest_sbs_pdf.py --pdf-path data/20160719_res-11356-2008.pdf --skip-gcs
```

Ingesta con embeddings:

```powershell
uv run python scripts/ingest_sbs_pdf.py --pdf-path data/20160719_res-11356-2008.pdf --with-embeddings
```

Regenerar embeddings sin reingestar:

```powershell
uv run python scripts/embed_chunks.py --all
```

Probar busqueda:

```powershell
uv run python scripts/search_chunks.py "categoria deficiente dias atraso"
```

## Reglas Estructuradas

Seeds disponibles:

```text
data/provision_rules_seed.csv
data/fcc_rules_seed.csv
```

Cargar seeds:

```powershell
uv run python scripts/seed_provision_rules.py
uv run python scripts/seed_fcc_rules.py
```

Inventario de tablas revisado:

```text
docs/table_inventory.md
```

## Validacion

Backend:

```powershell
uv run pytest
uv run ruff check .
uv run black --check .
```

Frontend:

```powershell
cd frontend
npm.cmd run build
```

Evaluacion offline del asistente:

```powershell
uv run python tests/eval/run_eval.py --base-url http://127.0.0.1:8000
```

Tambien puede ejecutarse contra Cloud Run pasando `--base-url`, credenciales Firebase y el dataset `tests/eval/sbs_validation_questions.json`.

## Despliegue

El despliegue productivo usa dos servicios de Cloud Run:

```text
sbs-assistant-api
sbs-assistant-web
```

URL actual de produccion:

```text
Frontend: https://sbs-assistant-web-578607935536.us-central1.run.app
Backend:  https://sbs-assistant-api-578607935536.us-central1.run.app
```

La guia operativa esta en:

```text
docs/deployment_cloud_run.md
```

GitHub Actions usa:

- Workload Identity Federation
- Artifact Registry
- Cloud Run
- Secret Manager para `DB_PASSWORD`
- Firebase Auth

## Notas de Seguridad

- No commitear `.env`, `frontend/.env`, PDFs locales, `.venv`, `node_modules` ni `dist`.
- `DB_PASSWORD` productivo vive en Secret Manager.
- Para produccion, `FIREBASE_AUTH_REQUIRED=true`.
- Si cambia la contrasena de Cloud SQL, actualizar tambien el secreto `DB_PASSWORD`.
