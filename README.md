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

The repository currently contains a **deployable vertical slice**: a single FastAPI container
that serves the landing/status page, a health endpoint, and **real NVIDIA model incident
analysis** at `POST /api/v1/incidents/analyze`.

```
Operational event → OBSERVE → NVIDIA model analysis → UNDERSTAND → DECIDE → structured response
```

Persistence and the remaining loop stages (`ACT / REQUEST APPROVAL`, `VERIFY`, `LEARN`) are
not implemented yet. `recommended_actions` are recommendations only — nothing executes
remediation.

## Architecture

One process, one container, no external services:

```
sentinel/api.py       FastAPI app — GET /health, GET /, POST /api/v1/incidents/analyze
sentinel/analysis.py  OBSERVE → UNDERSTAND → DECIDE, plus the Sentinel approval policy
sentinel/nvidia.py    NVIDIA Build client: forced tool call, timeouts, provider error taxonomy
sentinel/schemas.py   IncidentEvent / Assessment / IncidentAnalysis contracts
static/index.html     Landing/status page (plain HTML, no build step)
Dockerfile            python:3.13-slim, non-root UID 10001, HEALTHCHECK on /health
requirements.txt      Fully pinned runtime dependencies
```

There is no database, cache, queue, or auth layer in this slice by design; the only outbound
dependency is the NVIDIA Build API. See
[`docs/architecture/incident-analysis.md`](docs/architecture/incident-analysis.md) for the
analysis path, failure modes and privacy boundary.

## Local development

Requires Python 3.13.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

export NVIDIA_API_KEY=nvapi-...            # never commit this
export NVIDIA_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
uvicorn sentinel.api:app --reload
```

Then open <http://127.0.0.1:8000> for the landing page and <http://127.0.0.1:8000/health> for the health check.

Run the tests (they mock the provider at the HTTP transport layer, so no API key is needed):

```bash
python -m pytest
```

### With Docker

```bash
docker build -t novabrain-sentinel .
docker run --rm -p 8000:8000 \
  -e NVIDIA_API_KEY="$NVIDIA_API_KEY" \
  -e NVIDIA_MODEL="nvidia/nemotron-3.5-lightning-30b-a3b" \
  novabrain-sentinel
curl -s http://127.0.0.1:8000/health
```

## Configuration

Copy `.env.example` to `.env` to override defaults. `SENTINEL_*` variables all have working
defaults; the NVIDIA variables are read per request and are required only by the analysis
endpoint.

| Variable | Default | Purpose |
|---|---|---|
| `SENTINEL_HOST` | `0.0.0.0` | Bind address |
| `SENTINEL_PORT` | `8000` | Listen port |
| `SENTINEL_LOG_LEVEL` | `info` | uvicorn log level |
| `SENTINEL_ENV` | `production` | Deployment label |
| `NVIDIA_API_KEY` | *(none)* | Bearer token for NVIDIA Build. **Required** for analysis; never committed |
| `NVIDIA_BASE_URL` | `https://integrate.api.nvidia.com/v1` | OpenAI-compatible endpoint |
| `NVIDIA_MODEL` | *(none)* | Model id, used exactly as configured — no implicit fallback |

Without `NVIDIA_API_KEY` / `NVIDIA_MODEL`, `POST /api/v1/incidents/analyze` returns `503
provider_not_configured` while `GET /` and `GET /health` keep working.

## API

| Method | Path | Response |
|---|---|---|
| `GET` | `/health` | `200` → `{"status":"ok","service":"novabrain-sentinel"}` |
| `GET` | `/` | `200` → landing/status page |
| `POST` | `/api/v1/incidents/analyze` | `200` → structured assessment; `422` invalid event; `502`/`503`/`504` provider failure |

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/incidents/analyze \
  -H 'Content-Type: application/json' \
  --max-time 120 \
  -d '{
        "source": "novaops",
        "title": "API latency spike",
        "description": "p95 latency increased from 180ms to 2.4s",
        "severity_hint": "unknown",
        "evidence": ["error rate increased to 8.2%", "CPU increased to 91%"]
      }'
```

```json
{
  "incident_id": "inc_0b86102788ac4420bbeae77574c1a1d2",
  "status": "analyzed",
  "assessment": {
    "summary": "A p95 latency spike from 180 ms to 2.4 s is accompanied by an 8.2 % error rate and CPU utilization at 91 %, indicating severe performance degradation.",
    "severity": "high",
    "confidence": 0.87,
    "likely_causes": ["Resource exhaustion due to sustained high CPU usage", "…"],
    "recommended_actions": ["Investigate recent code deployments or configuration changes", "…"],
    "requires_approval": true,
    "reasoning_summary": "The combination of sharply increased latency, elevated error rate, and near-capacity CPU usage indicates a high-impact incident requiring immediate attention."
  },
  "model": { "provider": "nvidia", "model": "nvidia/nemotron-3.5-lightning-30b-a3b" }
}
```

Provider failures are structured too:

```json
{ "detail": { "error": "provider_timeout", "message": "NVIDIA did not respond within the allowed time" } }
```

## Deployment

Deployed as a Dockerfile-built application on Coolify. See [`docs/deployment/coolify.md`](docs/deployment/coolify.md).

## NVIDIA Model Integration

Inference runs on **NVIDIA Build** (`https://integrate.api.nvidia.com/v1`), an
OpenAI-compatible endpoint, using the NVIDIA open-source model
`nvidia/nemotron-3.5-lightning-30b-a3b`. Calls are made with `httpx` directly — no OpenAI
SDK, one attempt per request, no retries and no model fallback.

- **Event classification** — `severity` and `confidence` are decided from the evidence, and
  an `unknown` hint does not anchor the result.
- **Natural language understanding** — `summary` and `likely_causes` from the free-text event.
- **Reasoning and recommendations** — `reasoning_summary` (a concise rationale, not a
  chain-of-thought trace) and advisory `recommended_actions`.
- **Human-in-the-loop** — `requires_approval` is a Sentinel policy:
  `model_requires_approval OR severity in {high, critical}`. The model can add an approval
  requirement; it can never remove one from a high/critical incident.
- **Structured output** — forced tool calling: the assessment arrives in
  `tool_calls[0].function.arguments` and is validated by pydantic. If any required field is
  missing or malformed, the endpoint returns `502 invalid_model_response` rather than
  filling in a plausible value.

Nemotron is a reasoning model and thinks before it emits the tool call, so **live analysis
takes roughly 13–48 seconds** end to end. The client read timeout is `90s`; the caller and
any proxy in front of the service need to allow more than that. Measurements are in
[`docs/evaluation/`](docs/evaluation/).

`GET /health` never calls the model, so platform health checks stay instant regardless of
provider latency.


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
