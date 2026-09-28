# Architecture

NovaBrain Sentinel runs as one FastAPI process in one container: no database, cache, queue,
or auth layer. Incident workflow state lives in that process's memory, which makes single
replica a correctness requirement rather than a preference.

| Document | Covers |
|---|---|
| [incident-analysis.md](incident-analysis.md) | `POST /api/v1/incidents/analyze` — the OBSERVE → UNDERSTAND → DECIDE slice, NVIDIA forced-tool-call integration, approval policy, privacy boundary, failure modes, measured latency |
| [approval-workflow.md](approval-workflow.md) | `GET /api/v1/incidents/{id}` and the approve / reject / execute routes — the state machine, the execution invariant, the audit trail, simulated remediation, in-memory store semantics and its eviction rule |

Design decisions with their alternatives are in [`../decisions/`](../decisions/); deployment
constraints are in [`../deployment/coolify.md`](../deployment/coolify.md).

## Module map

```
sentinel/api.py       HTTP surface: GET /, GET /health, and the analyze / workflow routes
sentinel/analysis.py  cognitive sequence + Sentinel approval policy
sentinel/nvidia.py    provider config, request payload, HTTP call, error taxonomy
sentinel/schemas.py   request/response contracts, workflow states, action names, audit event
sentinel/workflow.py  state machine, approval gate, audit trail, in-memory store
sentinel/simulation.py  simulated action catalog — the only code that "does" anything
static/index.html     landing & status page (plain HTML, no build step)
Dockerfile            python:3.13-slim, curl for the platform healthcheck, non-root UID 10001
```

The dependency arrows point one way: `workflow.py` imports `simulation` and `schemas`, and
`api.py` imports both legs. Nothing in `analysis.py` or `nvidia.py` imports the workflow, so
the model-facing path is unchanged by everything downstream of it.
