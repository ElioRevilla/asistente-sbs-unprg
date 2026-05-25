# Despliegue en Cloud Run con GitHub Actions

Este proyecto despliega dos servicios en Cloud Run:

- `sbs-assistant-api`: backend FastAPI.
- `sbs-assistant-web`: frontend React/Vite servido con Nginx.

El workflow `.github/workflows/deploy.yml` usa Workload Identity Federation, no llaves JSON.

## 1. Crear repo GitHub

Crear un repositorio vacio en GitHub, por ejemplo:

```text
ElioRevilla/asistente-sbs-unprg
```

Luego, desde la raiz local:

```powershell
git init
git add .
git commit -m "feat: initial sbs assistant"
git branch -M main
git remote add origin https://github.com/ElioRevilla/asistente-sbs-unprg.git
git push -u origin main
```

## 2. Preparar GCP

Variables para los comandos:

```powershell
$PROJECT_ID="sbs-assistant-unprg"
$REGION="us-central1"
$REPOSITORY="sbs-assistant"
$GITHUB_REPO="ElioRevilla/asistente-sbs-unprg"
$DEPLOY_SA="github-deployer@$PROJECT_ID.iam.gserviceaccount.com"
$RUN_SA="sbs-assistant-run@$PROJECT_ID.iam.gserviceaccount.com"
$POOL_ID="github-actions"
$PROVIDER_ID="github"
```

Habilitar APIs necesarias:

```powershell
gcloud.cmd services enable `
  artifactregistry.googleapis.com `
  run.googleapis.com `
  iamcredentials.googleapis.com `
  cloudresourcemanager.googleapis.com `
  secretmanager.googleapis.com `
  cloudsql.googleapis.com `
  aiplatform.googleapis.com `
  firebase.googleapis.com `
  identitytoolkit.googleapis.com `
  --project=$PROJECT_ID
```

Crear Artifact Registry:

```powershell
gcloud.cmd artifacts repositories create $REPOSITORY `
  --repository-format=docker `
  --location=$REGION `
  --description="SBS Assistant containers" `
  --project=$PROJECT_ID
```

Crear service accounts:

```powershell
gcloud.cmd iam service-accounts create github-deployer `
  --display-name="GitHub Actions deployer" `
  --project=$PROJECT_ID

gcloud.cmd iam service-accounts create sbs-assistant-run `
  --display-name="SBS Assistant Cloud Run runtime" `
  --project=$PROJECT_ID
```

Roles del deployer:

```powershell
gcloud.cmd projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$DEPLOY_SA" `
  --role="roles/artifactregistry.writer"

gcloud.cmd projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$DEPLOY_SA" `
  --role="roles/run.admin"

gcloud.cmd iam service-accounts add-iam-policy-binding $RUN_SA `
  --member="serviceAccount:$DEPLOY_SA" `
  --role="roles/iam.serviceAccountUser" `
  --project=$PROJECT_ID
```

Roles del runtime:

```powershell
gcloud.cmd projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$RUN_SA" `
  --role="roles/cloudsql.client"

gcloud.cmd projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$RUN_SA" `
  --role="roles/aiplatform.user"

gcloud.cmd projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$RUN_SA" `
  --role="roles/firebaseauth.admin"

gcloud.cmd projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$RUN_SA" `
  --role="roles/secretmanager.secretAccessor"

gcloud.cmd projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$RUN_SA" `
  --role="roles/storage.objectUser"
```

Crear secret de password de PostgreSQL:

```powershell
$DB_PASSWORD="REEMPLAZAR_PASSWORD_REAL"
printf $DB_PASSWORD | gcloud.cmd secrets create DB_PASSWORD `
  --data-file=- `
  --replication-policy=automatic `
  --project=$PROJECT_ID
```

## 3. Workload Identity Federation

Crear pool y provider:

```powershell
gcloud.cmd iam workload-identity-pools create $POOL_ID `
  --project=$PROJECT_ID `
  --location=global `
  --display-name="GitHub Actions"

gcloud.cmd iam workload-identity-pools providers create-oidc $PROVIDER_ID `
  --project=$PROJECT_ID `
  --location=global `
  --workload-identity-pool=$POOL_ID `
  --display-name="GitHub" `
  --issuer-uri="https://token.actions.githubusercontent.com" `
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.ref=assertion.ref" `
  --attribute-condition="assertion.repository == '$GITHUB_REPO'"
```

Permitir que ese repo use el deployer:

```powershell
$PROJECT_NUMBER = gcloud.cmd projects describe $PROJECT_ID --format="value(projectNumber)"

gcloud.cmd iam service-accounts add-iam-policy-binding $DEPLOY_SA `
  --project=$PROJECT_ID `
  --role="roles/iam.workloadIdentityUser" `
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/attribute.repository/$GITHUB_REPO"
```

Valor para el secret de GitHub:

```powershell
"projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/providers/$PROVIDER_ID"
```

## 4. Variables y secrets en GitHub

Secrets:

```text
GCP_WORKLOAD_IDENTITY_PROVIDER=projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions/providers/github
GCP_DEPLOY_SERVICE_ACCOUNT=github-deployer@sbs-assistant-unprg.iam.gserviceaccount.com
VITE_FIREBASE_API_KEY=valor_de_frontend/.env
```

Variables:

```text
GCP_PROJECT_ID=sbs-assistant-unprg
GCP_REGION=us-central1
ARTIFACT_REPOSITORY=sbs-assistant
CLOUD_RUN_BACKEND_SERVICE=sbs-assistant-api
CLOUD_RUN_FRONTEND_SERVICE=sbs-assistant-web
CLOUD_RUN_SERVICE_ACCOUNT=sbs-assistant-run@sbs-assistant-unprg.iam.gserviceaccount.com
CLOUDSQL_INSTANCE=sbs-postgres
DB_NAME=sbs_assistant
DB_USER=postgres
GCS_BUCKET_DOCS=sbs-assistant-unprg-docs
FIREBASE_PROJECT_ID=sbs-assistant-unprg
VITE_FIREBASE_AUTH_DOMAIN=sbs-assistant-unprg.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=sbs-assistant-unprg
VITE_FIREBASE_APP_ID=1:578607935536:web:6c08d609b0b69bef067df5
VERTEX_AI_LOCATION=us-central1
GEMINI_FLASH_MODEL=gemini-2.5-flash
GEMINI_PRO_MODEL=gemini-2.5-pro
EMBEDDINGS_MODEL=text-embedding-005
```

## 5. Desplegar

Hacer push a `main` o ejecutar manualmente el workflow `Deploy Cloud Run`.

El workflow:

1. Construye y publica la imagen backend.
2. Despliega backend en Cloud Run.
3. Lee la URL real del backend.
4. Construye el frontend con `VITE_API_BASE_URL` apuntando al backend.
5. Despliega frontend en Cloud Run.
6. Actualiza CORS del backend con la URL real del frontend.
