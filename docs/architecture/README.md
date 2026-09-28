# Architecture

NovaBrain Sentinel runs as one FastAPI process in one container: no database, cache, queue or
session layer. Incident workflow state lives in that process's memory, which makes single
replica a correctness requirement rather than a preference. One shared bearer secret guards one
route (`POST /api/v1/events/ingest`); every other surface is public by design.

| Document | Covers |
|---|---|
| [incident-analysis.md](incident-analysis.md) | `POST /api/v1/incidents/analyze` — the OBSERVE → UNDERSTAND → DECIDE slice, NVIDIA forced-tool-call integration, approval policy, privacy boundary, failure modes, measured latency |
| [approval-workflow.md](approval-workflow.md) | `GET /api/v1/incidents/{id}` and the approve / reject / execute routes — the state machine, the execution invariant, the audit trail, simulated remediation, in-memory store semantics and its eviction rule |
| [machine-event-ingestion.md](machine-event-ingestion.md) | `POST /api/v1/events/ingest` — the producer contract, the bearer guard and its exact scope, the in-process idempotency ledger and its failure modes, the `event_ingested` audit event, the `/?incident=<id>` console bridge, synchronous limits |
| [operational-console.md](operational-console.md) | `GET /` — the three static files, the rendering contract (state / numbers / order come from the response), the console-scoped CSP, the error taxonomy in product language, the drift guards |

Design decisions with their alternatives are in [`../decisions/`](../decisions/); deployment
constraints are in [`../deployment/coolify.md`](../deployment/coolify.md).

## Module map

```
sentinel/api.py       HTTP surface: GET /, GET /health, and the analyze / ingest / workflow routes
sentinel/analysis.py  cognitive sequence + Sentinel approval policy
sentinel/nvidia.py    provider config, request payload, HTTP call, error taxonomy
sentinel/ingestion.py bearer-token guard + in-process idempotency ledger for machine events
sentinel/schemas.py   request/response contracts, workflow states, action names, audit event
sentinel/workflow.py  state machine, approval gate, audit trail, in-memory store
sentinel/simulation.py  simulated action catalog — the only code that "does" anything
static/index.html     the demo console — markup and prefilled incident (plain HTML, no build step)
static/styles.css     console styling on the existing design tokens
static/app.js         console behaviour: same-origin fetch, render-from-response, no framework
scripts/send_demo_event.py  demo event emitter — a NovaOps-compatible producer, stdlib only
Dockerfile            python:3.13-slim, curl for the platform healthcheck, non-root UID 10001
```

The dependency arrows point one way: `workflow.py` imports `simulation` and `schemas`, and
`api.py` imports both legs plus `ingestion`. Nothing in `analysis.py` or `nvidia.py` imports the
workflow or the ingestion guard, so the model-facing path is unchanged by everything downstream
of it — an ingested event and a console-submitted one run through identical analysis code.
