# Deploying NovaBrain Sentinel with Coolify

This slice ships as **one container**. No database, queue, or backing service is required.
The only outbound dependency is the NVIDIA Build inference API, used by
`POST /api/v1/incidents/analyze`.

Incident workflow state (approval gate, audit trail, verification results) is held **in the
process memory** — see [Run as exactly one replica](#run-as-exactly-one-replica).

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

## Run as exactly one replica

Set Coolify's instance/replica count to **1** and keep the service on a single node. The
`Dockerfile` command is `exec python -m uvicorn sentinel.api:app` — one worker, one process —
and the workflow store is that process's memory.

Two replicas break the approval workflow in a way that looks like a bug:

- `POST …/analyze` is served by replica A, so the incident exists only in A's store. A request
  routed to replica B answers `404 incident_not_found`.
- An incident an operator approved on A can be *re-*analysed by B, which is a fresh store with
  a fresh `incident_id`. Nothing is shared, so nothing is deduplicated.
- The audit trail for one incident must be one append-only list. Splitting it across processes
  would make the ordering guarantee in
  [`docs/architecture/approval-workflow.md`](../architecture/approval-workflow.md) untrue.

Scaling this service means replacing the in-memory store with a shared one first (see
ADR-0002). It is not a knob to turn here.

Restarting the container is a clean reset: every tracked incident, its approval decision and
its audit trail are gone. That is the documented behaviour of this slice, not a data-loss
regression.

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

The approval workflow adds **no new environment variables** and no new dependencies: there is
no store to point at, no credential to issue, nothing to configure. Existing deployments
redeploy cleanly.

There is also **no authentication token to set** — the workflow endpoints are unauthenticated
in this slice, so protect them at the platform layer (Coolify domain, Traefik auth middleware,
IP allowlist, or an internal network) rather than exposing `POST …/execute` publicly.

A deployment without `NVIDIA_API_KEY` / `NVIDIA_MODEL` is still valid: `GET /` and
`GET /health` work, and the analysis endpoint answers `503 provider_not_configured` naming
the missing variables only. Because incidents enter the workflow store through the analysis
endpoint, an unconfigured deployment has an empty store and every
`GET /api/v1/incidents/{incident_id}` answers `404 incident_not_found`.

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

Keep the `incident_id` from that response and walk the approval gate on the same deployment
(same process, so the store still holds the record):

```bash
ID=inc_...   # incident_id from the response above

# 1. the workflow record exists
curl -sS https://<your-domain>/api/v1/incidents/$ID

# 2. execution is refused before approval — this 409 is the gate proving it works
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://<your-domain>/api/v1/incidents/$ID/execute \
  -H 'Content-Type: application/json' -d '{"action":"scale_api_replicas"}'

# 3. approve, then execute once
curl -s -X POST https://<your-domain>/api/v1/incidents/$ID/approve \
  -H 'Content-Type: application/json' -d '{"note":"checked the dashboards, proceeding"}'
curl -s -X POST https://<your-domain>/api/v1/incidents/$ID/execute \
  -H 'Content-Type: application/json' -d '{"action":"scale_api_replicas","note":"simulated"}'
```

Expected: step 2 returns `409` with
`{"detail":{"error":"approval_required","message":"This incident is awaiting an operator approval."}}`;
step 3 returns `200` for the approval and `200` with `state: "verified"` for the execution. The
final `GET` shows the whole audit trail — including an `execution_blocked` event for step 2,
because refusals are audited too. **Nothing real is touched** — the action is simulated;
`verification.simulated` is `true` in the payload.

The image declares a Docker `HEALTHCHECK` that polls `/health` every 30s using the Python standard library, so Coolify and Docker both surface container health without an external probe binary. The image also installs `curl` so Coolify's own HTTP healthcheck can run inside the container.

## Rollback

Redeploy the previous commit from `main`. There is no migration or data step to reverse: the
only persisted state is the in-memory workflow store, which a redeploy discards. Open
incidents (awaiting approval or approved but not yet executed) are lost, and their `incident_id`
will answer `404` after the rollback — operators re-analyse rather than resume.

Commits before the NVIDIA integration do not have the analysis endpoint at all; commits before
TASK-012 do not have the workflow routes, so a rolled-back deployment will answer `404` for
`/api/v1/incidents/{incident_id}` even for ids that existed before the rollback.

