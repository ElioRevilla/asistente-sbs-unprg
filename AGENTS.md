# AGENTS.md

## Proyecto

Asistente educativo multimodal sobre la Resolucion SBS N. 11356-2008 para estudiantes universitarios de Economia, Administracion, Contabilidad y Derecho. La aplicacion final sera una PWA en espanol LATAM con cinco modos pedagogicos: Explicame, Ejemplifica, Compara, Evaluame y Aplica.

## Estado Actual

Workspace: `D:\Electronica-IA\asistente-unprg`

Backend inicial implementado con:

- Python >= 3.12
- FastAPI
- Pydantic v2 / pydantic-settings
- Clean Architecture basica
- pytest, ruff, black
- uv y `uv.lock`

Frontend inicial implementado en `frontend/` con:

- React 18 + Vite + TypeScript
- TanStack Query + axios
- Zustand para estado de sesion Firebase
- Firebase Authentication con email/password
- Backend valida ID tokens con `firebase-admin`
- lucide-react para iconos
- Pantalla de login Firebase
- Pantalla principal como chat unico con selector de modo `Explicame` / `Ejemplifica`

Config Firebase frontend:

```text
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=sbs-assistant-unprg.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=sbs-assistant-unprg
VITE_FIREBASE_APP_ID=
```

Config Firebase backend:

```env
FIREBASE_AUTH_REQUIRED=false
FIREBASE_PROJECT_ID=sbs-assistant-unprg
```

En local `FIREBASE_AUTH_REQUIRED=false` mantiene los endpoints utilizables sin token.
Para produccion, usar `FIREBASE_AUTH_REQUIRED=true`.

Endpoint disponible:

- `GET /health`

Comando local que funciona:

```powershell
python -m uvicorn sbs_assistant.api.main:app --reload
```

Tambien funciona con uv:

```powershell
uv run uvicorn sbs_assistant.api.main:app --reload
```

Comandos frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
npm.cmd run build
```

Despliegue preparado:

- Backend Cloud Run: `sbs-assistant-api`
- Frontend Cloud Run: `sbs-assistant-web`
- Artifact Registry repo esperado: `sbs-assistant`
- Workflow real: `.github/workflows/deploy.yml`
- Guia: `docs/deployment_cloud_run.md`
- Usa GitHub Actions + Workload Identity Federation, sin llaves JSON.

## Decision De Infraestructura

Se cambio la decision inicial de AlloyDB a:

- Cloud Storage
- Cloud SQL PostgreSQL 16
- pgvector

Motivo: menor costo y suficiente para el MVP/paper. La arquitectura sigue siendo compatible con una migracion futura a AlloyDB porque ambos son PostgreSQL-compatible.

No usar variables `ALLOYDB_*`. La configuracion visible usa:

```env
CLOUDSQL_INSTANCE=sbs-postgres
DB_HOST=
DB_PORT=5432
DB_NAME=sbs_assistant
DB_USER=postgres
DB_PASSWORD=
```

## Recursos GCP Creados

Proyecto:

- `sbs-assistant-unprg`

Region principal:

- `us-central1`

APIs habilitadas:

- Cloud SQL Admin API
- Cloud Storage
- Vertex AI
- Compute
- Service Networking

Bucket:

- `sbs-assistant-unprg-docs`
- location: `us-central1`

Cloud SQL:

- instancia: `sbs-postgres`
- version: `POSTGRES_16`
- tier: `db-f1-micro`
- region: `us-central1`
- estado verificado: `RUNNABLE`
- base creada: `sbs_assistant`

Autenticacion:

- `gcloud auth login` realizado
- `gcloud auth application-default login` realizado
- ADC quota project configurado a `sbs-assistant-unprg`

## Base De Datos

Migracion aplicada:

- `db/migrations/001_initial_schema.sql`

Incluye:

- extension `vector`
- extension `pgcrypto`
- `chunks`
- `provision_rules`
- `students`
- `concept_mastery`
- `quiz_bank`
- `quiz_attempts`
- `synthetic_cases`
- `session_log`

Script recomendado:

```powershell
uv run python scripts/setup_postgres.py
```

Estado verificado:

```text
Skipping 001_initial_schema.sql
```

Eso significa que la migracion ya fue aplicada y el script conecta correctamente a Cloud SQL.

## Modulo De Ingesta

Implementado:

- `IngestDocumentUseCase`
- descarga HTTP de PDF
- lectura local de PDF con `--pdf-path`
- parser inicial con `pypdf`
- chunking por articulo con `SbsRegulationTextChunker`
- extraccion basica de reglas de provision
- repositorios PostgreSQL para `chunks` y `provision_rules`
- opcion de GCS para subir el PDF original
- opcion de Vertex AI para embeddings

Scripts:

```powershell
uv run python scripts/ingest_sbs_pdf.py
uv run python scripts/ingest_sbs_pdf.py --skip-gcs
uv run python scripts/ingest_sbs_pdf.py --pdf-path "C:\ruta\al\pdf.pdf" --skip-gcs
uv run python scripts/ingest_sbs_pdf.py --pdf-path "C:\ruta\al\pdf.pdf" --with-embeddings
```

Importante: la URL oficial de SBS devuelve HTML anti-bot de Incapsula cuando la descarga Python. Para continuar, descargar el PDF manualmente desde el navegador y ejecutar la ingesta con `--pdf-path`.

Estado actual de ingesta:

- PDF local ubicado en `data/20160719_res-11356-2008.pdf`
- La ingesta sin embeddings se ejecuto contra Cloud SQL.
- `chunks` quedo cargado con secciones numeradas del reglamento.
- `provision_rules` quedo cargado con 65 reglas curadas desde `data/provision_rules_seed.csv`.
- Las tablas cubiertas en `provision_rules` son: tabla general para categoria Normal, Tabla 1 sin garantia/no cubierto, Tabla 2 con garantia preferida, Tabla 3 con garantia preferida de muy rapida realizacion, garantia preferida autoliquidable, componente prociclico del Anexo I, tratamiento prociclico con garantias preferidas autoliquidables, convenio de descuento por planilla elegible y tabla de constitucion gradual Mes 2 / Mes 4 / Mes 6.
- Los factores de conversion crediticios (FCC) se cargan en la tabla propia `fcc_rules` desde `data/fcc_rules_seed.csv`.
- Inventario visual/textual de tablas disponible en `docs/table_inventory.md`.
- El chunker ya limpia footers de pagina y numeros de pagina sueltos; esto corrigio el caso en que el numero de pagina `19` cortaba indebidamente el numeral `3.4 CATEGORIA DUDOSO`.
- Reingesta posterior dejo `sec_027_3_4` con la regla minorista completa: atraso de sesenta y uno (61) a ciento veinte (120) dias calendario.
- El chunker etiqueta secciones de categoria por tipo de cartera:
  - `2.x` categoria -> `cartera_no_minorista`
  - `3.x` categoria -> `cartera_minorista`
  - `4.x` categoria -> `cartera_hipotecaria_vivienda`
- Embeddings reales regenerados con Vertex AI `text-embedding-005` para los 115 chunks actuales.
- Retriever hibrido PostgreSQL implementado con pgvector, full text search en espanol y Reciprocal Rank Fusion.
- Modo `Explicame` implementado en `POST /modes/explain`.
- `Explicame` usa `PostgresHybridRetriever`, Gemini Flash y prompt anti-alucinacion con respuesta maxima de 200 palabras y citas.
- `Explicame` pasa metadata de cartera al prompt y filtra las citas finales para mostrar solo fuentes usadas por la respuesta.
- Prueba real con la pregunta `En que casos un deudor se clasifica en categoria Dudoso?` devolvio respuesta estructurada por cartera y solo citas `2.4`, `3.4`, `4.4`.
- `Explicame` tiene un calculador deterministico minimo para casos simples con monto, dias de atraso y tipo de credito minorista/hipotecario. Si detecta un caso calculable, responde por codigo y consulta `provision_rules`; no delega el porcentaje ni el monto al LLM.
- Caso validado: consumo no revolvente, S/ 10,000 y 75 dias de atraso -> categoria Dudoso, Tabla 1 asumida si no hay garantia, 60%, provision S/ 6,000.
- Se agrego `RetrievalPlanner` en `application/services/retrieval_planner.py`. Para preguntas como `Cuantos tipos de credito existen y cuales son?`, el backend eleva internamente `top_k` a 10 y responde con lista canonica de ocho tipos sin depender del LLM; la cita visible se limita al Numeral 4.
- `RetrievalPlanner` tambien detecta preguntas sobre permanencia prolongada en categorias `Dudoso` o `Perdida`. Reescribe la query interna hacia la regla tecnica (`Dudoso mas de 36 meses`, `Perdida mas de 24 meses`, `Tabla 1`) y `Explicame` responde determinísticamente: aplicar Tabla 1; para `Perdida`, provision 100%.
- Modo `Ejemplifica` inicial implementado con plantillas deterministicas auditables:
  - `POST /modes/example/generate`
  - `POST /modes/example/answer`
  - Genera casos por categoria desde `TemplateExampleCaseGenerator`.
  - Persiste en `synthetic_cases` con `PostgresSyntheticCaseRepository`.
  - Valida la respuesta del estudiante contra la categoria correcta guardada.
  - Soporta variacion narrativa opcional con Gemini Flash usando `use_llm_variation=true`.
  - La variacion LLM solo puede modificar campos narrativos seguros (`nombre_deudor`, `rubro`, `situacion`).
  - Categoria correcta, dias de atraso, monto, tipo de credito, fuente y provision se preservan desde la plantilla/codigo.
  - Si el concepto incluye `microempresa`, genera un caso de credito a microempresa (`CreditType.MES`) usando los criterios de cartera minorista del Capitulo II, numeral 3.x. Ejemplo validado: microempresa en categoria Deficiente -> 45 dias de atraso, fuente numeral 3.3.
- Prueba end-to-end real de `/modes/explain` contra Cloud SQL + Vertex AI devolvio HTTP 200.

Conteos verificados en Cloud SQL:

```text
chunks=115
chunks_with_embeddings=115
provision_rules=65
fcc_rules=5
```

## Calidad

Ultima validacion conocida:

```text
pytest: 47 passed
ruff: OK
black: OK
npm.cmd run build: OK
setup_postgres.py: OK
```

Comandos:

```powershell
uv run pytest
uv run ruff check .
uv run black --check .
cd frontend
npm.cmd run build
```

## Archivos Importantes

- `sbs_assistant/api/main.py`
- `sbs_assistant/config/settings.py`
- `sbs_assistant/application/use_cases/ingest_document.py`
- `sbs_assistant/infrastructure/parsing/sbs_text_chunker.py`
- `sbs_assistant/infrastructure/parsing/pypdf_document_parser.py`
- `sbs_assistant/infrastructure/persistence/connection.py`
- `sbs_assistant/infrastructure/retrieval/postgres_hybrid_retriever.py`
- `sbs_assistant/infrastructure/llm/vertex_gemini_client.py`
- `sbs_assistant/application/use_cases/explain_concept.py`
- `sbs_assistant/application/prompts/explain.py`
- `sbs_assistant/api/routes/explain.py`
- `frontend/src/app/App.tsx`
- `frontend/src/features/auth/LoginPage.tsx`
- `frontend/src/features/chat/AssistantChat.tsx`
- `frontend/src/services/apiClient.ts`
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `.github/workflows/ci.yml`
- `.github/workflows/deploy.yml`
- `docs/deployment_cloud_run.md`
- `scripts/setup_postgres.py`
- `scripts/setup_postgres_migrations.py`
- `scripts/ingest_sbs_pdf.py`
- `scripts/embed_chunks.py`
- `scripts/search_chunks.py`
- `db/migrations/001_initial_schema.sql`
- `db/migrations/002_create_fcc_rules.sql`
- `scripts/seed_provision_rules.py`
- `scripts/seed_fcc_rules.py`
- `docs/table_inventory.md`
- `.env.example`
- `.env` existe localmente pero no debe commitearse.

## Proximos Pasos

1. Refinar metadata/contexto de chunks para distinguir mejor criterios por tipo de credito cuando una categoria aparece en varias secciones.
2. Implementar `/chat` minimo con `forced_mode=explicame` o router automatico simple.
3. Antes de usar las reglas para evaluacion academica, hacer revision humana contra el PDF fuente. La extraccion inicial fue con `pypdf` y curacion manual, no con Document AI.

## Advertencias Tecnicas

- `vertexai.language_models.TextEmbeddingModel` funciona, pero mostro warning de deprecacion del SDK Vertex AI generativo con remocion anunciada para 2026-06-24. Antes del despliegue final conviene migrar el adaptador de embeddings al SDK recomendado por Google.

## Notas Para Codex

- No crear AlloyDB salvo que el usuario lo pida explicitamente.
- Mantener cambios pequenos e iterativos.
- No implementar mas de un modulo mayor por turno sin confirmacion.
- No commitear `.env` ni secretos.
- Si se necesita red o GCP, usar `gcloud.cmd` en PowerShell porque `gcloud.ps1` puede estar bloqueado por ExecutionPolicy.
- Si el puerto 5432 falla desde red local, usar Cloud SQL Python Connector; ya esta integrado.
