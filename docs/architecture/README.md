# Architecture

NovaBrain Sentinel runs as one FastAPI process in one container: no database, cache, queue,
or auth layer.

| Document | Covers |
|---|---|
| [incident-analysis.md](incident-analysis.md) | `POST /api/v1/incidents/analyze` — the OBSERVE → UNDERSTAND → DECIDE slice, NVIDIA forced-tool-call integration, approval policy, privacy boundary, failure modes, measured latency |

Design decisions with their alternatives are in [`../decisions/`](../decisions/); deployment
constraints are in [`../deployment/coolify.md`](../deployment/coolify.md).

## Module map

```
sentinel/api.py       HTTP surface: GET /, GET /health, POST /api/v1/incidents/analyze
sentinel/analysis.py  cognitive sequence + Sentinel approval policy
sentinel/nvidia.py    provider config, request payload, HTTP call, error taxonomy
sentinel/schemas.py   IncidentEvent / Assessment / IncidentAnalysis contracts
static/index.html     landing & status page (plain HTML, no build step)
Dockerfile            python:3.13-slim, curl for the platform healthcheck, non-root UID 10001
```
