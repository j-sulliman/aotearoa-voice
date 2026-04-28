#!/usr/bin/env bash
# Aotearoa Voice — Cloud Run alternative deploy.
#
# The primary deploy path is local Docker + Cloudflare Tunnel (see
# deploy/cloudflared.config.yml). This script is the secondary path: three
# Cloud Run services (mcp_server → backend → frontend), wired up so the
# stack runs entirely on managed GCP.
#
# Prerequisites:
#   - gcloud CLI authenticated (gcloud auth login)
#   - A GCP project with billing enabled and Cloud Run + Artifact Registry APIs on:
#       gcloud services enable run.googleapis.com artifactregistry.googleapis.com
#   - Secrets created in Secret Manager (see SECRET_NAMES below) OR exported
#     as env vars before running this script.
#
# Usage:
#   PROJECT_ID=my-project REGION=australia-southeast1 ./deploy.sh

set -euo pipefail

PROJECT_ID="${PROJECT_ID:?set PROJECT_ID}"
REGION="${REGION:-australia-southeast1}"
REPO="${REPO:-aotearoa-voice}"

# Service names — Cloud Run will assign URLs of the form
#   https://<service>-<hash>-<region>.a.run.app
MCP_SERVICE="aotearoa-mcp"
BACKEND_SERVICE="aotearoa-backend"
FRONTEND_SERVICE="aotearoa-frontend"

# Secrets the backend needs. Either create these in Secret Manager:
#   echo -n "$ANTHROPIC_API_KEY" | gcloud secrets create anthropic-api-key --data-file=-
# …or export them in this shell and the script will read them out.
SECRET_NAMES=(anthropic-api-key openai-api-key elevenlabs-api-key elevenlabs-voice-id)

cd "$(dirname "$0")/../.."

echo "==> Project: $PROJECT_ID  Region: $REGION  Repo: $REPO"
gcloud config set project "$PROJECT_ID" >/dev/null

# 1. Artifact Registry repo (idempotent)
echo "==> Ensuring Artifact Registry repo $REPO exists"
gcloud artifacts repositories describe "$REPO" --location="$REGION" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "$REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Aotearoa Voice demo containers"

REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet >/dev/null

# 2. Build + push images
build_and_push() {
  local name=$1 context=$2
  echo "==> Building $name"
  docker build --platform linux/amd64 -t "${REGISTRY}/${name}:latest" "$context"
  docker push "${REGISTRY}/${name}:latest"
}

build_and_push "$MCP_SERVICE" ./mcp_server
build_and_push "$BACKEND_SERVICE" ./backend
# Frontend image needs API_BASE_URL baked in at build time. We deploy backend
# first so we have its URL, then re-build the frontend pointing at it.
# That means a two-pass deploy on first run; subsequent runs are one-pass.

# 3. Deploy MCP server (public — so Claude Desktop and the backend can both reach it)
echo "==> Deploying $MCP_SERVICE"
gcloud run deploy "$MCP_SERVICE" \
  --image "${REGISTRY}/${MCP_SERVICE}:latest" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8001 \
  --cpu 1 --memory 512Mi \
  --min-instances 0 --max-instances 3 \
  --quiet

MCP_URL=$(gcloud run services describe "$MCP_SERVICE" --region "$REGION" --format='value(status.url)')
echo "    MCP at $MCP_URL"

# 4. Deploy backend (with secrets + MCP URL)
echo "==> Deploying $BACKEND_SERVICE"

SECRET_FLAGS=()
for name in "${SECRET_NAMES[@]}"; do
  env_var=$(echo "$name" | tr a-z- A-Z_)
  SECRET_FLAGS+=(--update-secrets="${env_var}=${name}:latest")
done

gcloud run deploy "$BACKEND_SERVICE" \
  --image "${REGISTRY}/${BACKEND_SERVICE}:latest" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --cpu 1 --memory 1Gi \
  --min-instances 0 --max-instances 5 \
  --timeout 60 \
  --set-env-vars "MCP_SERVER_URL=${MCP_URL}/sse,ANTHROPIC_MODEL=claude-sonnet-4-6,WHISPER_MODEL=whisper-1,ELEVENLABS_MODEL_ID=eleven_multilingual_v2,ELEVENLABS_PRONUNCIATION_DICTIONARY_ID=${ELEVENLABS_PRONUNCIATION_DICTIONARY_ID:-},ELEVENLABS_PRONUNCIATION_DICTIONARY_VERSION_ID=${ELEVENLABS_PRONUNCIATION_DICTIONARY_VERSION_ID:-},RATE_LIMIT_PER_MINUTE=20,LOG_LEVEL=INFO" \
  "${SECRET_FLAGS[@]}" \
  --quiet

BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" --region "$REGION" --format='value(status.url)')
echo "    Backend at $BACKEND_URL"

# 5. Build the frontend with the live backend URL baked in, then deploy
echo "==> Building $FRONTEND_SERVICE pointing at $BACKEND_URL"
docker build --platform linux/amd64 \
  --build-arg "API_BASE_URL=${BACKEND_URL}" \
  -t "${REGISTRY}/${FRONTEND_SERVICE}:latest" \
  ./frontend
docker push "${REGISTRY}/${FRONTEND_SERVICE}:latest"

echo "==> Deploying $FRONTEND_SERVICE"
gcloud run deploy "$FRONTEND_SERVICE" \
  --image "${REGISTRY}/${FRONTEND_SERVICE}:latest" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 5173 \
  --cpu 1 --memory 256Mi \
  --min-instances 0 --max-instances 5 \
  --quiet

FRONTEND_URL=$(gcloud run services describe "$FRONTEND_SERVICE" --region "$REGION" --format='value(status.url)')

# 6. Update backend CORS to allow the frontend's URL
echo "==> Updating backend CORS to allow $FRONTEND_URL"
gcloud run services update "$BACKEND_SERVICE" \
  --region "$REGION" \
  --update-env-vars "ALLOWED_ORIGINS=${FRONTEND_URL}" \
  --quiet

echo
echo "Done."
echo "  MCP:      $MCP_URL/sse"
echo "  Backend:  $BACKEND_URL"
echo "  Frontend: $FRONTEND_URL"
