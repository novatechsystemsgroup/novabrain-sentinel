# Deploying NovaBrain Sentinel with Coolify

This slice ships as **one container**. No database, queue, or backing service is required.
The only outbound dependency is the NVIDIA Build inference API, used by
`POST /api/v1/incidents/analyze`.

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

`SENTINEL_*` variables are optional — the image supplies defaults. The `NVIDIA_*` variables
are required for `POST /api/v1/incidents/analyze` and are read per request.

| Variable | Default | Purpose |
|---|---|---|
| `SENTINEL_HOST` | `0.0.0.0` | Bind address |
| `SENTINEL_PORT` | `8000` | Listen port; must match the domain port |
| `SENTINEL_LOG_LEVEL` | `info` | uvicorn log level |
| `SENTINEL_ENV` | `production` | Deployment label |
| `NVIDIA_API_KEY` | *(none)* | Bearer token for NVIDIA Build. **Required** for incident analysis |
| `NVIDIA_BASE_URL` | `https://integrate.api.nvidia.com/v1` | OpenAI-compatible endpoint; override only for a different region/endpoint |
| `NVIDIA_MODEL` | *(none)* | **Required.** Set to `nvidia/nemotron-3.5-lightning-30b-a3b`; there is no fallback model |

**Secrets:** `NVIDIA_API_KEY` is the only sensitive value in this list. Add it as a Coolify
**secret** environment variable (build-time and run-time) rather than a plain variable, so it
is masked in the UI and not written into committed files. Never commit it, and never put a
real value in `.env.example`.

A deployment without `NVIDIA_API_KEY` / `NVIDIA_MODEL` is still valid: `GET /` and
`GET /health` work, and the analysis endpoint answers `503 provider_not_configured` naming
the missing variables only.

## Request timeout

Live NVIDIA analyses measured **13–48 seconds** end to end, because Nemotron reasons before
it returns the structured assessment. The application allows up to **90 seconds** of read
time on the provider call (`READ_TIMEOUT` in `sentinel/nvidia.py`).

Set the service's proxy/request timeout **above 90 seconds** (Coolify: *Configuration →
Advanced → HTTP timeout / Read timeout*, or the equivalent Traefik/Caddy middleware
timeout). If the proxy times out first, the operator sees a proxy-generated `502`/`504`
instead of Sentinel's own `{"detail":{"error":"provider_timeout",…}}`, and the inference
cost is paid for nothing.

`GET /health` never calls the model, so Docker's `HEALTHCHECK` and Coolify's health probe are
unaffected by this latency budget.

## Verify the deployment

```bash
curl -sSf https://<your-domain>/health
```

Expected response, HTTP 200:

```json
{"status":"ok","service":"novabrain-sentinel"}
```

Then load `https://<your-domain>/` and confirm the landing page renders **NovaBrain Sentinel**, the six-stage cognitive loop, and **System Status: Operational**.

Finally, confirm the model path is wired and the secret is in place:

```bash
curl -s --max-time 120 -X POST https://<your-domain>/api/v1/incidents/analyze \
  -H 'Content-Type: application/json' \
  -d '{"source":"manual","title":"API latency spike","description":"p95 180ms -> 2.4s","severity_hint":"unknown","evidence":["error rate 8.2%","CPU 91%"]}'
```

Expect `200` with `status: "analyzed"`, a `high` or `critical` severity for that event, and
`requires_approval: true`. A `503` means the NVIDIA variables are missing from the deployment;
a `502 provider_unavailable` means the key was rejected or the endpoint was unreachable.

The image declares a Docker `HEALTHCHECK` that polls `/health` every 30s using the Python standard library, so Coolify and Docker both surface container health without an external probe binary. The image also installs `curl` so Coolify's own HTTP healthcheck can run inside the container.

## Rollback

Redeploy the previous commit from `main`. The application is stateless, so there is no
migration or data step to reverse — but note that commits before the NVIDIA integration do
not have the analysis endpoint at all.

