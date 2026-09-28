# Deploying NovaBrain Sentinel with Coolify

This slice ships as **one container**. No database, queue, or external service is required.

## Resource summary

| Setting | Value |
|---|---|
| Repository | `https://github.com/novatechsystemsgroup/novabrain-sentinel` |
| Branch | `main` |
| Build type | Dockerfile |
| Dockerfile path | `Dockerfile` (repository root) |
| Build context | repository root (`.`) |
| Application port | `8000` (set via `SENTINEL_PORT`) |
| Health check path | `/health` |

## Create the service

1. In Coolify choose **+ New resource → Application**.
2. Select **Git repository** and paste the repository URL above.
3. Set **Branch** to `main`.
4. Set **Build type** to **Dockerfile**.
5. Confirm **Dockerfile location** is `Dockerfile` and **Build context directory** is the repository root.
6. Coolify derives the container name from the project; no compose file is involved.

## Network

- The container listens on `0.0.0.0:${SENTINEL_PORT}`, default `8000`.
- Point Coolify's **Domains** entry at port `8000`. If you change `SENTINEL_PORT`, change the exposed domain port to match.
- The image already declares `EXPOSE 8000` and runs as UID `10001`, so no privileged settings are needed.

## Environment variables

All are optional — the image supplies defaults. Add them under the service's **Environment Variables** tab only when you need to override.

| Variable | Default | Purpose |
|---|---|---|
| `SENTINEL_HOST` | `0.0.0.0` | Bind address |
| `SENTINEL_PORT` | `8000` | Listen port; must match the domain port |
| `SENTINEL_LOG_LEVEL` | `info` | uvicorn log level |
| `SENTINEL_ENV` | `production` | Deployment label |
| `NVIDIA_API_KEY` | *(empty)* | Reserved for the model-integration task; unused by this slice |
| `NVIDIA_BASE_URL` | *(empty)* | Reserved, as above |
| `NVIDIA_MODEL` | *(empty)* | Reserved, as above |

**Secrets:** `NVIDIA_API_KEY` is the only sensitive value in this list. Provide it through Coolify's secret environment variables at deploy time. Never commit it, and never add it to `.env.example` with a real value.

This slice makes no model calls, so a successful deployment does not require any NVIDIA credentials.

## Verify the deployment

```bash
curl -sSf https://<your-domain>/health
```

Expected response, HTTP 200:

```json
{"status":"ok","service":"novabrain-sentinel"}
```

Then load `https://<your-domain>/` and confirm the landing page renders **NovaBrain Sentinel**, the six-stage cognitive loop, and **System Status: Operational**.

The image declares a Docker `HEALTHCHECK` that polls `/health` every 30s using the Python standard library, so Coolify and Docker both surface container health without an external probe binary.

## Rollback

Redeploy the previous commit from `main`. The application is stateless, so there is no migration or data step to reverse.
