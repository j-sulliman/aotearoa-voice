# Cloud Run alternative deploy

The primary deploy path is local Docker + Cloudflare Tunnel — see [`deploy/cloudflared.config.yml`](../cloudflared.config.yml). This folder is the secondary path: three managed Cloud Run services, no host machine to keep online.

## Why offer both

- **Local Docker + tunnel** is zero-cost, self-hosted, and matches the production architecture I run for Summit53. Best for the demo lifecycle.
- **Cloud Run** is the better answer if the demo URL needs to stay up while my workstation is off, or if a reviewer wants to clone the repo and stand it up themselves on infrastructure they control.

The application code is identical — every service has a Dockerfile and is independently deployable. The only difference is how the three services discover each other.

## Prerequisites

- A Google Cloud project with billing enabled
- `gcloud` CLI installed and authenticated (`gcloud auth login`)
- The Cloud Run + Artifact Registry APIs enabled:
  ```bash
  gcloud services enable run.googleapis.com artifactregistry.googleapis.com
  ```
- Docker running locally (the script builds `linux/amd64` images and pushes them)

## Secrets

The backend needs four secrets — store them in Secret Manager once:

```bash
echo -n "$ANTHROPIC_API_KEY"     | gcloud secrets create anthropic-api-key     --data-file=-
echo -n "$OPENAI_API_KEY"        | gcloud secrets create openai-api-key        --data-file=-
echo -n "$ELEVENLABS_API_KEY"    | gcloud secrets create elevenlabs-api-key    --data-file=-
echo -n "$ELEVENLABS_VOICE_ID"   | gcloud secrets create elevenlabs-voice-id   --data-file=-
```

Then grant Cloud Run's runtime service account access:

```bash
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
for s in anthropic-api-key openai-api-key elevenlabs-api-key elevenlabs-voice-id; do
  gcloud secrets add-iam-policy-binding "$s" \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role=roles/secretmanager.secretAccessor
done
```

## Deploy

```bash
PROJECT_ID=my-project REGION=australia-southeast1 ./deploy.sh
```

The script:

1. Ensures an Artifact Registry repo exists.
2. Builds and pushes the `mcp_server` and `backend` images.
3. Deploys the MCP server (public — so the backend and any external MCP client can both reach it at `/sse`).
4. Deploys the backend, wiring `MCP_SERVER_URL` to the MCP service's URL and pulling the four API keys from Secret Manager.
5. Builds the frontend image with the **backend's URL baked in** at compile time (`VITE_API_BASE_URL`), pushes it, and deploys the frontend service.
6. Updates the backend's `ALLOWED_ORIGINS` to permit the frontend's URL.

## Architecture on Cloud Run

```
                                Internet
                                    │
                                    ▼
                  ┌──────────────────────────────┐
                  │ aotearoa-frontend (5173)     │
                  │  static SPA, public          │
                  └──────────────┬───────────────┘
                                 │ fetch
                                 ▼
                  ┌──────────────────────────────┐
                  │ aotearoa-backend (8000)      │
                  │  FastAPI orchestrator        │
                  │  reads secrets from SM       │
                  └──────────────┬───────────────┘
                                 │ MCP/SSE
                                 ▼
                  ┌──────────────────────────────┐
                  │ aotearoa-mcp (8001)          │
                  │  FastMCP, public so          │
                  │  Claude Desktop also works   │
                  └──────────────────────────────┘
```

## Optional: pronunciation dictionary

Run [`scripts/setup_pronunciation_dict.py`](../../scripts/setup_pronunciation_dict.py) **once locally** before deploying — it uploads the Te Reo Māori pronunciation dictionary to your ElevenLabs account and prints the IDs. Then export the IDs in the same shell as `deploy.sh`:

```bash
export ELEVENLABS_PRONUNCIATION_DICTIONARY_ID=...
export ELEVENLABS_PRONUNCIATION_DICTIONARY_VERSION_ID=...
PROJECT_ID=my-project ./deploy.sh
```

The script picks them up via `--set-env-vars`. Leaving them unset is fine — the deployed backend just uses the model's default pronunciation.

## Notes

- **Cold start.** All three services are scaled to zero by default. First request after idle takes ~1-2s extra. Bump `--min-instances 1` on `aotearoa-backend` if you need consistently low latency.
- **Region.** `australia-southeast1` (Sydney) is the closest Cloud Run region to NZ. Latency from Auckland is ~30ms.
- **Cost.** With scale-to-zero and the demo's traffic profile, expect <$1 USD/month for the Cloud Run side. Anthropic + ElevenLabs + OpenAI usage is the meaningful spend.
- **MCP server visibility.** The script makes it public so a reviewer can connect Claude Desktop to it without auth. If you'd rather keep it private, drop `--allow-unauthenticated` on `MCP_SERVICE` and use a Cloud Run-to-Cloud-Run service identity for the backend.
