# Asistente Educativo SBS

Aplicacion educativa sobre la Resolucion SBS N. 11356-2008 para estudiantes universitarios. El proyecto combina un backend FastAPI con arquitectura limpia, PostgreSQL/pgvector en Cloud SQL, Vertex AI para embeddings y Gemini, Firebase Authentication y un frontend React/Vite desplegable en Cloud Run.

Estado actual:

- Backend FastAPI con modos `Explicame` y `Ejemplifica`.
- RAG hibrido con PostgreSQL, pgvector, full text search en espanol y RRF.
- Ingesta del PDF SBS con `pypdf`, chunking por secciones y embeddings Vertex AI.
- Reglas de provision y FCC cargadas desde seeds curados.
- Frontend React con login Firebase y chat unico con selector de modo.
- CI/CD con GitHub Actions hacia dos servicios de Cloud Run.

## Estructura del proyecto

```text
.
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
├── data/
│   ├── fcc_rules_seed.csv
│   └── provision_rules_seed.csv
├── db/
│   └── migrations/
│       ├── 001_initial_schema.sql
│       └── 002_create_fcc_rules.sql
├── docs/
│   ├── deployment_cloud_run.md
│   └── table_inventory.md
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── App.tsx
│   │   │   └── Dashboard.tsx
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   │   ├── LoginPage.tsx
│   │   │   │   └── authStore.ts
│   │   │   └── chat/
│   │   │       └── AssistantChat.tsx
│   │   ├── services/
│   │   │   ├── apiClient.ts
│   │   │   └── firebase.ts
│   │   ├── shared/
│   │   │   ├── apiTypes.ts
│   │   │   └── markdown.tsx
│   │   ├── main.tsx
│   │   └── styles.css
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── vite.config.ts
├── sbs_assistant/
│   ├── api/
│   │   ├── auth/
│   │   │   └── firebase.py
│   │   ├── routes/
│   │   │   ├── example.py
│   │   │   ├── explain.py
│   │   │   └── health.py
│   │   ├── schemas/
│   │   │   ├── request_schemas.py
│   │   │   └── response_schemas.py
│   │   └── main.py
│   ├── application/
│   │   ├── prompts/
│   │   │   └── explain.py
│   │   ├── services/
│   │   │   ├── example_case_templates.py
│   │   │   ├── llm_example_variation.py
│   │   │   └── retrieval_planner.py
│   │   └── use_cases/
│   │       ├── calculate_provision.py
│   │       ├── explain_concept.py
│   │       ├── generate_example.py
│   │       ├── ingest_document.py
│   │       └── validate_example_answer.py
│   ├── config/
│   │   └── settings.py
│   ├── domain/
│   │   ├── entities/
│   │   ├── ports/
│   │   └── value_objects/
│   └── infrastructure/
│       ├── embeddings/
│       ├── llm/
│       ├── parsing/
│       ├── persistence/
│       ├── retrieval/
│       └── storage/
├── scripts/
│   ├── check_ingestion_counts.py
│   ├── embed_chunks.py
│   ├── ingest_sbs_pdf.py
│   ├── search_chunks.py
│   ├── seed_fcc_rules.py
│   ├── seed_provision_rules.py
│   ├── setup_postgres.py
│   └── setup_postgres_migrations.py
├── tests/
│   ├── integration/
│   └── unit/
├── .env.example
├── Dockerfile
├── pyproject.toml
└── uv.lock
```

## Capas principales

### Backend

- `sbs_assistant/domain`: entidades, value objects y ports. No debe depender de FastAPI, PostgreSQL, Vertex AI ni Firebase.
- `sbs_assistant/application`: casos de uso y servicios de aplicacion. Contiene la logica pedagogica, planificacion de retrieval y calculos deterministas.
- `sbs_assistant/infrastructure`: adaptadores concretos para PostgreSQL, Cloud SQL, Vertex AI, Gemini, GCS, parsing del PDF y retrieval hibrido.
- `sbs_assistant/api`: app FastAPI, rutas HTTP, schemas y autenticacion Firebase.
- `sbs_assistant/config`: settings con Pydantic Settings y variables de entorno.

### Frontend

- `frontend/src/features/auth`: login Firebase y estado de sesion.
- `frontend/src/features/chat`: interfaz principal tipo chat con selector `Explicame` / `Ejemplifica`.
- `frontend/src/services`: cliente HTTP y configuracion Firebase.
- `frontend/src/shared`: tipos compartidos y renderizado de markdown.

### Datos y despliegue

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

## Setup local

Instalar dependencias Python:

```powershell
uv sync --all-groups
```

Si PowerShell no reconoce `uv`, instalarlo primero o usar el ejecutable del entorno virtual si ya existe.

Copiar variables base:

```powershell
Copy-Item .env.example .env
```

Completar `.env` con las credenciales locales necesarias. No commitear `.env`.

## Ejecutar backend

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

## Ejecutar frontend

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

## Endpoints implementados

```http
GET  /health
POST /modes/explain
POST /modes/example/generate
POST /modes/example/answer
```

`/modes/explain` usa retrieval hibrido, Gemini Flash y citas obligatorias.

`/modes/example/*` genera y valida casos sinteticos auditables. La variacion narrativa con Gemini es opcional y solo modifica campos seguros.

## Base de datos y migraciones

Las migraciones viven en `db/migrations` y se ejecutan en orden lexicografico.

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

## Reglas estructuradas

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

## Notas de seguridad

- No commitear `.env`, `frontend/.env`, PDFs locales, `.venv`, `node_modules` ni `dist`.
- `DB_PASSWORD` productivo vive en Secret Manager.
- Para produccion, `FIREBASE_AUTH_REQUIRED=true`.
- Si cambia la contrasena de Cloud SQL, actualizar tambien el secreto `DB_PASSWORD`.
