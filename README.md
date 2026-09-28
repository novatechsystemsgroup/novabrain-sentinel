# NovaBrain Sentinel

**Event-driven operational agent for the NVIDIA Claw Agent Challenge: London**

NovaBrain Sentinel receives operational events from a monitoring system, assesses each one with a
live NVIDIA Nemotron call, and parks anything rated `high` or `critical` behind a human approval
gate before a response can run. It is deliberately not an incident chatbot: nobody types a
question and reads prose back. A producer posts one event over HTTP, the model returns a
schema-validated structured assessment, Sentinel's own deterministic policy decides whether an
operator is required, and every step — including the attempts the policy refused — is appended to
an audit trail. The model supplies judgement; the safety around it is plain code.

**Live demo: <https://sentinel.novatechsystem.co.uk>** — no login, no setup, one page.
**Model: `nvidia/nemotron-3.5-lightning-30b-a3b` on NVIDIA Build.**
**Inference is real; remediation is simulated, and the console says so on screen.**

## The loop, and what each stage actually does

```
OBSERVE → UNDERSTAND → DECIDE → ACT / REQUEST APPROVAL → VERIFY → LEARN
```

1. **OBSERVE** — **real.** One operational event arrives over HTTP, from a machine producer or from the console form.
2. **UNDERSTAND** — **real.** Nemotron returns severity, confidence, likely causes, recommended actions and a concise rationale, validated by pydantic.
3. **DECIDE** — **real.** Sentinel's approval policy decides whether an operator is required — not the model.
4. **ACT / REQUEST APPROVAL** — **gate real, action simulated.** An approved action runs against a closed two-entry catalog. No service is restarted and nothing is scaled.
5. **VERIFY** — **simulated.** Deterministic before/after snapshots, not a measurement of anything.
6. **LEARN** — **not implemented.** No memory, no model updates, no policy refinement.

## Status

**Early implementation / Hackathon build** — Active development for the NVIDIA Claw Agent Challenge: London.

The repository currently contains a **deployable vertical slice**: a single FastAPI container
that serves an **operational demo console** at `/`, a health endpoint, **bearer-token machine
event ingestion**, **real NVIDIA model incident analysis**, and an **approval-gated workflow**
with an audit trail. A judge can open one URL and walk the whole loop without curl, Postman or
developer tools — see
[`docs/architecture/operational-console.md`](docs/architecture/operational-console.md).

```
producer event (or console form) → OBSERVE → NVIDIA model analysis → UNDERSTAND → DECIDE
       → awaiting approval → operator APPROVE / REJECT → ACT (simulated) → VERIFY (simulated)
```

What is real and what is not:

| Stage | Status |
|---|---|
| `OBSERVE` / `UNDERSTAND` | **Real** — a producer's event is ingested over HTTP and a live NVIDIA Build call produces and validates the assessment |
| `DECIDE` | **Real** — Sentinel's approval policy parks high/critical incidents behind an operator gate |
| `ACT / REQUEST APPROVAL` | Gate is real; the action is **simulated**. Nothing is restarted or scaled |
| `VERIFY` | **Simulated** — deterministic before/after metric snapshots |
| `LEARN` | Not implemented |

`recommended_actions` remain advisory text. No endpoint performs real remediation, and
persistence (`LEARN` included) is not implemented yet — workflow state lives in the process.

## Architecture

One process, one container, no external services:

```
sentinel/api.py       FastAPI app — GET /health, GET /, and the analyze / workflow routes
sentinel/analysis.py  OBSERVE → UNDERSTAND → DECIDE, plus the Sentinel approval policy
sentinel/nvidia.py    NVIDIA Build client: forced tool call, timeouts, provider error taxonomy
sentinel/ingestion.py bearer-token guard + in-process idempotency ledger for machine events
sentinel/workflow.py  state machine, approval gate, audit trail, in-memory store
sentinel/simulation.py  simulated action catalog — the only code that "does" anything
sentinel/schemas.py   contracts for the event, the assessment, the workflow state and audit events
static/index.html     The operational demo console — plain HTML, no build step
static/styles.css     Console styling on the existing design tokens
static/app.js         Console behaviour: same-origin fetch + render, no framework, no CDN
scripts/send_demo_event.py  demo event emitter (stdlib only) — a NovaOps-compatible producer
Dockerfile            python:3.13-slim, non-root UID 10001, HEALTHCHECK on /health
requirements.txt      Fully pinned runtime dependencies
```

There is no database, cache, queue or session layer in this slice by design, and one shared
bearer secret guards one route; the only outbound dependency is the NVIDIA Build API.
`analysis.py` and `nvidia.py` know nothing about the workflow or about ingestion, so the
model-facing path is unchanged by everything downstream of it.

See [`docs/architecture/incident-analysis.md`](docs/architecture/incident-analysis.md) for the
analysis path, failure modes and privacy boundary,
[`docs/architecture/approval-workflow.md`](docs/architecture/approval-workflow.md) for the
state machine, the execution invariant and the audit trail, and
[`docs/architecture/machine-event-ingestion.md`](docs/architecture/machine-event-ingestion.md)
for how a producer's event enters that workflow.

## Local development

Requires Python 3.13.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

export NVIDIA_API_KEY='paste your NVIDIA Build key here'   # never commit it
export NVIDIA_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
export SENTINEL_INGEST_TOKEN=$(openssl rand -hex 32)        # only POST /api/v1/events/ingest needs it
uvicorn sentinel.api:app --reload
```

Then open <http://127.0.0.1:8000> for the demo console and <http://127.0.0.1:8000/health> for the health check.
The console needs no separate server or port: FastAPI serves `static/` itself.

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
  -e SENTINEL_INGEST_TOKEN="$SENTINEL_INGEST_TOKEN" \
  novabrain-sentinel
curl -s http://127.0.0.1:8000/health
```

Passing `-e VAR` forwards the value from your shell into the container without it ever
appearing in the image, a commit or a log line. Omit the ingest line to leave machine
ingestion switched off.

## Configuration

Copy `.env.example` to `.env` to override defaults. `SENTINEL_*` variables all have working
defaults; the NVIDIA variables are read per request and are required by the analysis and
ingestion endpoints, while `SENTINEL_INGEST_TOKEN` is required only by the ingestion one.

| Variable | Default | Purpose |
|---|---|---|
| `SENTINEL_HOST` | `0.0.0.0` | Bind address |
| `SENTINEL_PORT` | `8000` | Listen port |
| `SENTINEL_LOG_LEVEL` | `info` | uvicorn log level |
| `SENTINEL_ENV` | `production` | Deployment label |
| `NVIDIA_API_KEY` | *(none)* | Bearer token for NVIDIA Build. **Required** for analysis; never committed |
| `NVIDIA_BASE_URL` | `https://integrate.api.nvidia.com/v1` | OpenAI-compatible endpoint |
| `NVIDIA_MODEL` | *(none)* | Model id, used exactly as configured — no implicit fallback |
| `SENTINEL_INGEST_TOKEN` | *(none)* | Shared bearer secret presented by a machine producer. **Required** only by `POST /api/v1/events/ingest`; never committed, logged or echoed |

Without `NVIDIA_API_KEY` / `NVIDIA_MODEL`, `POST /api/v1/incidents/analyze` returns `503
provider_not_configured` while `GET /` and `GET /health` keep working. Without
`SENTINEL_INGEST_TOKEN`, `POST /api/v1/events/ingest` returns `503 ingest_not_configured` — the
route is switched off rather than left open, and every other endpoint is unaffected.

The approval workflow adds **no configuration**: no new variables, no dependencies, no backing
service. Its one limit is a compile-time constant (`MAX_TRACKED_INCIDENTS = 200`) documented in
[`docs/architecture/approval-workflow.md`](docs/architecture/approval-workflow.md).

Machine ingestion adds **one secret** and no dependency, no store and no backing service. Its
replay guard is per-process memory, so a restart clears it: an event replayed after a redeploy is
treated as new. That limit, and the `MAX_TRACKED_EVENTS = 200` ceiling beside it, are documented in
[`docs/architecture/machine-event-ingestion.md`](docs/architecture/machine-event-ingestion.md).

## API

| Method | Path | Response |
|---|---|---|
| `GET` | `/health` | `200` → `{"status":"ok","service":"novabrain-sentinel"}` |
| `GET` | `/` | `200` → the operational demo console (HTML, strict CSP on this response only) |
| `POST` | `/api/v1/incidents/analyze` | `200` → structured assessment; `422` invalid event; `502`/`503`/`504` provider failure |
| `POST` | `/api/v1/events/ingest` | `201` first receipt / `200` duplicate replay → incident pointer; `401` invalid ingest token; `409` event in progress; `422` invalid event; `502`/`503`/`504` provider or capacity failure |
| `GET` | `/api/v1/incidents/{incident_id}` | `200` → full workflow record; `404` unknown incident |
| `POST` | `/api/v1/incidents/{incident_id}/approve` | `200` → updated record; `409` not awaiting approval |
| `POST` | `/api/v1/incidents/{incident_id}/reject` | `200` → updated record; `409` not awaiting approval |
| `POST` | `/api/v1/incidents/{incident_id}/execute` | `200` → simulated action + verification; `409` blocked; `422` unknown action |

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

### Approval workflow

`POST /api/v1/incidents/analyze` also files the incident in the workflow store. A `high` or
`critical` assessment opens in `awaiting_approval` and cannot act until an operator decides.
Execution is allowed **iff** `requires_approval` is false **or** the incident is `approved` —
and `rejected` incidents never execute, permanently.

```bash
ID=inc_ae3dc4898d774d938d1b7053d796ba8a

curl -s -X POST http://127.0.0.1:8000/api/v1/incidents/$ID/execute \
  -H 'Content-Type: application/json' -d '{"action":"scale_api_replicas"}'
# 409 {"detail":{"error":"approval_required","message":"This incident is awaiting an operator approval."}}

curl -s -X POST http://127.0.0.1:8000/api/v1/incidents/$ID/approve \
  -H 'Content-Type: application/json' -d '{"note":"Approved for simulated scale-out."}'
# 200 {"state":"approved", …}

curl -s -X POST http://127.0.0.1:8000/api/v1/incidents/$ID/execute \
  -H 'Content-Type: application/json' -d '{"action":"scale_api_replicas"}'
# 200 {"state":"verified", "verification":{"status":"verified","simulated":true, …}}
```

The `verification` block is the simulated outcome, not a measurement:

```json
{
  "status": "verified",
  "simulated": true,
  "before": { "api_replicas": 2, "p95_latency_ms": 2400, "error_rate_percent": 8.2, "service_restarts": 0 },
  "after":  { "api_replicas": 4, "p95_latency_ms": 610,  "error_rate_percent": 0.4, "service_restarts": 0 },
  "success": true
}
```

`GET /api/v1/incidents/{incident_id}` returns the whole evidence bundle — the original event,
the NVIDIA assessment, the state, the approval decision, the selected action, the verification
and the ordered audit trail. This is a real trail from a live run (one genuine analysis, one
premature attempt, one approval, one simulated action, one repeat attempt):

```
18:49:55.710578  incident_analyzed      sentinel  {"severity":"high","confidence":0.92,"requires_approval":true,…}
18:49:55.710785  approval_requested     sentinel  {"severity":"high","reason":"Sentinel approval policy requires an operator decision."}
18:49:55.731204  execution_blocked      operator  {"action":"scale_api_replicas","reason":"approval_required"}
18:49:55.734057  approval_granted       operator  {"note":"Approved for simulated scale-out on the demo cluster."}
18:49:55.735724  execution_requested    operator  {"action":"scale_api_replicas","mode":"simulated","note":"simulated only"}
18:49:55.735797  execution_finished     sentinel  {"action":"scale_api_replicas","state":"verified"}
18:49:55.735801  verification_recorded  sentinel  {"status":"verified","success":true,"simulated":true}
18:49:55.737154  execution_blocked      operator  {"action":"restart_api_service","reason":"already_executed"}
```

Blocked attempts are audited too: a refusal leaves a record of what was asked and why it was
denied. **Append order is the authoritative sequence** — adjacent events may share a timestamp,
so read the list in order rather than sorting by `timestamp`.

The surface is closed: an operator can only `approve` or `reject`, and the action catalog has
exactly two entries, `scale_api_replicas` and `restart_api_service`. Anything else is a `422`
before the store sees it. `restart_api_service` on a `critical` incident deterministically
yields `failed`, which is how both terminal outcomes stay demonstrable without randomness.

## Machine event ingestion

`POST /api/v1/events/ingest` is the machine door: another process reports an event, Sentinel
normalises it into the same `IncidentEvent` the console builds, and the existing
analysis → approval → execute → audit workflow takes it from there. **The operator no longer
creates the incident manually** — they review the one a producer opened.

```bash
export SENTINEL_INGEST_TOKEN=$(openssl rand -hex 32)   # must match the server's value

curl -s -X POST http://127.0.0.1:8000/api/v1/events/ingest \
  -H "Authorization: Bearer $SENTINEL_INGEST_TOKEN" \
  -H 'Content-Type: application/json' \
  --max-time 120 \
  -d '{
        "event_id": "novaops-evt-2026-09-28-0007",
        "source": "novaops",
        "event_type": "ram_high",
        "title": "Memory pressure on api-01",
        "description": "Host agent reports sustained memory pressure",
        "severity_hint": "warning",
        "evidence": ["error rate increased to 8.2%", "CPU increased to 91%"],
        "observed_at": "2026-09-28T08:15:00+00:00"
      }'
```

```json
{
  "event_id": "novaops-evt-2026-09-28-0007",
  "incident_id": "inc_0b86102788ac4420bbeae77574c1a1d2",
  "workflow_state": "awaiting_approval",
  "duplicate": false,
  "console_path": "/?incident=inc_0b86102788ac4420bbeae77574c1a1d2"
}
```

`201` on the first receipt, `200` with `"duplicate": true` when the same `event_id` is replayed —
the replay returns the incident it already made and **does not call the model again**.
`console_path` is relative on purpose (Sentinel does not know its public hostname), and opening
it loads that incident into the same console panels: the query parameter can only ever trigger a
same-origin fetch of an incident, never a request elsewhere.

Three properties worth stating precisely:

- **Auth.** Machine-to-machine ingestion is bearer-token protected. The public hackathon console
  remains intentionally unauthenticated, and so is `POST /api/v1/incidents/analyze`; the guard is
  one route wide, not an application-wide one. An unset token answers `503 ingest_not_configured`
  rather than leaving the route open.
- **Idempotency.** The ledger is in-process memory, so **a restart clears it** and an event
  replayed after a redeploy becomes a new incident. A duplicate arriving while its analysis is
  still running answers `409 event_in_progress`; a full ledger refuses with
  `503 ingest_ledger_full` instead of evicting an event being analysed.
- **Synchronous.** The request is held for the whole inference (**7–47 s** measured, `90 s`
  provider read timeout), so the caller's timeout must exceed the backend's. There is no queue,
  worker or callback: this is an idempotency-guarded door for a low event rate, not a
  high-throughput webhook receiver.

`scripts/send_demo_event.py` is the demo producer — a **NovaOps-compatible producer**, not a
NovaOps integration (see the architecture doc for what NovaOps actually emits today). It reads
the token from the environment only, never takes it as an argument, never prints it, and posts one
`ram_high` event:

```bash
.venv/bin/python scripts/send_demo_event.py --url http://127.0.0.1:8000 --event-id novaops-demo-0001
# HTTP 201
# event_id: novaops-demo-0001
# incident_id: inc_…
# workflow_state: awaiting_approval
# duplicate: False
# console_path: /?incident=inc_…
```

Full contract, normalisation rules, failure taxonomy and the audit ordering are in
[`docs/architecture/machine-event-ingestion.md`](docs/architecture/machine-event-ingestion.md),
with the trade-offs in
[`docs/decisions/0003-machine-event-ingestion.md`](docs/decisions/0003-machine-event-ingestion.md).

## Deployment

Deployed as a Dockerfile-built application on Coolify. Because workflow state is per-process,
this slice must run as **exactly one replica** — see
[`docs/deployment/coolify.md`](docs/deployment/coolify.md).

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
takes roughly 7–47 seconds** end to end. The client read timeout is `90s`; the caller and
any proxy in front of the service need to allow more than that. Measurements are in
[`docs/evaluation/`](docs/evaluation/).

`GET /health` never calls the model, so platform health checks stay instant regardless of
provider latency.


## Demo

**<https://sentinel.novatechsystem.co.uk>** — the operational console, no login.

Two ways in, and the second is the one that makes the loop honest:

1. **Machine-first (the story being told).** A producer posts an event
   (`scripts/send_demo_event.py` with `SENTINEL_INGEST_TOKEN` in its environment), Sentinel
   ingests it, analyses it with a live NVIDIA call, files the incident in the same workflow store
   the console reads (so a `high` or `critical` assessment opens in `awaiting_approval`), and
   returns a `/?incident=…` link. The operator clicks that link and finds the incident already
   there — **the operator no longer creates the incident manually.** Re-running the emitter with
   the same `event_id` answers `200 duplicate: true` and hands back the same incident without
   paying for a second inference.
2. **Console-driven.** The same four clicks below, with the incident typed into the page.

Four clicks, no page reload, no developer tools:

| # | Click | What the page shows |
|---|---|---|
| 1 | **Run Demo Incident** | a spinner and real elapsed seconds while NVIDIA Nemotron assesses the prefilled incident (7–47 s), then severity, confidence, provider/model, summary, likely causes, recommended actions and the "Decision rationale" |
| 2 | **Attempt Execution** | `409 approval_required` rendered as *"Execution blocked by Sentinel policy — approval is required before this action can run"*, and the audit trail gains `execution_blocked`. This is the safety feature, not an error |
| 3 | **Approve** | the ⚠ HUMAN APPROVAL REQUIRED gate closes, the decision is recorded with actor, note and timestamp |
| 4 | **Execute** | `VERIFIED` with `Simulation: YES` and the before → after metric snapshots exactly as the backend returned them |

The trail below the panels holds all of it in append order, with Sentinel-authored events
visually distinct from operator-authored ones. **Clear / New Incident** resets the page for the
next judge.

Nothing in the demo path is a stub: submission, inference, severity, causes, recommendations,
the approval policy, the state machine and the audit trail are the production code paths. Only
the remediation and its measurements are simulated, and the page says so permanently.

## Evaluation

Measured runs of the shipped artifact are recorded in [`docs/evaluation/`](docs/evaluation/):

- **TASK-011** — two live NVIDIA analyses (12.8 s and 47.1 s for the same input), the leak
  checks, and what the latency spread means for the timeout budget.
- **TASK-012** — the full loop through the approval gate: real NVIDIA inference, then
  **simulated** execution and verification. It records the `awaiting_approval → 409 → approve
  → execute → verified` path, the permanent rejection path, the 8-event audit trail exactly as
  it came back, and the guard-rail responses (`422` unknown action, `404` unknown incident).

The label matters: **no run in this repository performed real remediation.** `verified` means
the simulated action's catalog outcome met its recovery condition, not that an incident was
resolved in the world.

## Security Principles

- **Human-in-the-loop** — `high` and `critical` incidents always require an operator decision;
  the model can add that requirement but never remove it, and no such incident executes autonomously
- **Fail closed** — execution is denied unless the invariant `requires_approval == false OR
  state == "approved"` holds; a rejected incident is permanently denied
- **Audit trail** — every transition and every *refused attempt* is recorded with actor and
  details; the store refuses to evict an unfinished incident rather than lose its trail
- **Nothing real is touched** — the action catalog is closed, typed, and marked
  `executes: False`. No workflow code spawns a process or opens a socket; the only outbound
  network call in the codebase is the NVIDIA inference request in `nvidia.py`
- **Least privilege** — Minimal permissions for each component
- **Console surface** — the page is locked to its own assets by a CSP on `GET /` alone
  (`script-src 'self'`, no inline script, no CDN, no `frame-ancestors`), calls only same-origin
  routes, and never sees the NVIDIA key, the ingest token, the provider base URL or any reasoning
  trace
- **Ingestion guard** — `POST /api/v1/events/ingest` requires a shared bearer secret compared
  with `hmac.compare_digest`, checked before the request body is parsed, and answered with
  `www-authenticate: Bearer` on failure. The token is never logged, echoed, stored, or shipped in
  an example
- **Secrets management** — No credentials in source code; environment-based configuration. Two
  secrets exist (`NVIDIA_API_KEY`, `SENTINEL_INGEST_TOKEN`), both runtime-only, and neither has a
  value in this repository or its docs
- **Input validation** — All external inputs are validated and sanitized
- **Defense in depth** — Multiple layers of security controls

Known gaps, stated rather than implied: Machine-to-machine ingestion is bearer-token protected.
The public hackathon console remains intentionally unauthenticated — as does
`POST /api/v1/incidents/analyze`, so any client that can reach the port can still pay for an
inference and approve its own incident (every actor is recorded as `operator` regardless of who
pressed it). One shared secret, with no rotation or per-producer identity, is a demo-grade
control: guard the rest at the platform layer. Workflow state is **in-memory only**, so an audit
trail does not survive a restart and neither does ingestion idempotency. Closing these is
follow-on work, not part of this slice.

## Repository Relationship

| Repository | Role |
|---|---|
| **NovaBrain** | Intelligence / control-plane source — reasoning, memory, decision models |
| **NovaOps** | Monitoring / operational source — telemetry, observability, incident data |
| **Sentinel** | Competition product — integrates reusable components from NovaBrain and NovaOps into a unified operational agent |

Sentinel is a separate repository that selectively reuses components from NovaBrain and NovaOps after architectural audit. It is not a fork or copy of either repository.

## License

See [LICENSE](LICENSE).
