# NovaBrain Sentinel

**Persistent Operational AI Agent for the NVIDIA Build Challenge**

NovaBrain Sentinel is an autonomous operational agent that continuously monitors, analyzes, and responds to system events through a structured cognitive loop.

## Core Loop

```
OBSERVE → UNDERSTAND → DECIDE → ACT / REQUEST APPROVAL → VERIFY → LEARN
```

1. **OBSERVE** — Ingest telemetry, logs, metrics, and external signals
2. **UNDERSTAND** — Classify events, detect anomalies, correlate context
3. **DECIDE** — Evaluate response options against policies and risk
4. **ACT / REQUEST APPROVAL** — Execute autonomous remediation or escalate to human operators
5. **VERIFY** — Confirm outcome, measure impact, detect regressions
6. **LEARN** — Update models, refine policies, improve future decisions

## Status

**Early implementation / Hackathon build** — Active development for the NVIDIA competition.

The repository currently contains a **deployable vertical slice**: a single FastAPI container that serves the landing/status page and a health endpoint. Model integration, persistence, and the agent loop itself are not implemented yet.

## Architecture

One process, one container, no external services:

```
sentinel/api.py     FastAPI app — GET /health, GET /
static/index.html   Landing/status page (plain HTML, no build step)
Dockerfile          python:3.13-slim, non-root UID 10001, HEALTHCHECK on /health
requirements.txt    Fully pinned runtime dependencies
```

There is no database, cache, queue, or auth layer in this slice by design. Deeper design documents go in [`docs/architecture/`](docs/architecture/).

## Local development

Requires Python 3.13.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

uvicorn sentinel.api:app --reload
```

Then open <http://127.0.0.1:8000> for the landing page and <http://127.0.0.1:8000/health> for the health check.

Run the tests:

```bash
pytest
```

### With Docker

```bash
docker build -t novabrain-sentinel .
docker run --rm -p 8000:8000 novabrain-sentinel
curl -s http://127.0.0.1:8000/health
```

## Configuration

Copy `.env.example` to `.env` to override defaults. All variables are optional; the application has working defaults.

| Variable | Default | Purpose |
|---|---|---|
| `SENTINEL_HOST` | `0.0.0.0` | Bind address |
| `SENTINEL_PORT` | `8000` | Listen port |
| `SENTINEL_LOG_LEVEL` | `info` | uvicorn log level |
| `SENTINEL_ENV` | `production` | Deployment label |

`NVIDIA_API_KEY`, `NVIDIA_BASE_URL` and `NVIDIA_MODEL` are reserved for the model-integration task and are not read by this slice. Never commit real credentials.

## API

| Method | Path | Response |
|---|---|---|
| `GET` | `/health` | `200` → `{"status":"ok","service":"novabrain-sentinel"}` |
| `GET` | `/` | `200` → landing/status page |

## Deployment

Deployed as a Dockerfile-built application on Coolify. See [`docs/deployment/coolify.md`](docs/deployment/coolify.md).

## NVIDIA Model Integration

NovaBrain Sentinel leverages NVIDIA AI foundation models and inference endpoints for:

- Event classification and anomaly detection
- Natural language understanding for incident analysis
- Decision reasoning and recommendation generation
- Automated remediation planning

> Integration details will be documented as implementation progresses.

## Demo

> Demo URL will be published here once the application is deployed.

## Evaluation

> Evaluation methodology, metrics, and results will be documented in [`docs/evaluation/`](docs/evaluation/).

## Security Principles

- **Least privilege** — Minimal permissions for each component
- **Human-in-the-loop** — Critical actions require operator approval
- **Audit trail** — All decisions and actions are logged
- **Secrets management** — No credentials in source code; environment-based configuration
- **Input validation** — All external inputs are validated and sanitized
- **Defense in depth** — Multiple layers of security controls

## Repository Relationship

| Repository | Role |
|---|---|
| **NovaBrain** | Intelligence / control-plane source — reasoning, memory, decision models |
| **NovaOps** | Monitoring / operational source — telemetry, observability, incident data |
| **Sentinel** | Competition product — integrates reusable components from NovaBrain and NovaOps into a unified operational agent |

Sentinel is a separate repository that selectively reuses components from NovaBrain and NovaOps after architectural audit. It is not a fork or copy of either repository.

## License

See [LICENSE](LICENSE).
