# Submission Copy

TASK-015 §12. Paste-ready blocks for the Airtable submission form. Every sentence survives the
audit in `claims-audit.md`: nothing here claims persistence, real remediation, NovaOps integration
or a `LEARN` loop. Word counts are printed per section and were measured, not estimated.

## Project name

```
NovaBrain Sentinel
```

## One-sentence tagline

```
An event-driven operational agent that receives monitoring events, assesses them with a real NVIDIA
Nemotron model, and refuses to act without a human approval.
```

## Problem

```
Operational incidents arrive faster than a person can read them, and the first minutes decide the
outage. Two failure modes sit at both ends of that gap. A human on-call triages an alert stream by
hand and burns the window on context-switching. An autonomous agent acts on its own, and nobody can
say afterwards why it touched what it touched. Most agent demos pick one of those halves: they show
fluent reasoning with no control boundary, or a workflow engine with no reasoning at all. Judging an
incident well is not the hard part alone. The hard part is being useful in the first minute while
leaving a decision a human can own and an audit line that explains it.
```
_(word count printed at the end of this file)_

## Solution

```
Sentinel takes the operational loop — OBSERVE, UNDERSTAND, DECIDE, ACT, VERIFY, AUDIT — and is
honest about which links it actually implements. Ingestion is real: a monitoring producer posts one
event to a bearer-protected route and gets an incident id back. The assessment is real: NVIDIA
Nemotron returns a severity, probable causes, recommended actions and a confidence value through a
forced, schema-validated tool call, so the answer arrives typed rather than as prose. The decision
is real but deterministic: a high or critical severity always raises the approval gate, and the
model can add that requirement but never remove it. Execution is simulated, and the console says so
on screen: a closed two-action catalog returns before/after metric snapshots instead of touching an
infrastructure API. The audit trail is real and append-ordered, including the times Sentinel refused
to act. One sentence covers the split: real NVIDIA inference, safe simulated remediation.
```

## How it works

```
A producer sends one event: source, event type, title, description, a severity hint and an evidence
list. The hint is only a hint. The route authenticates the bearer token before parsing the body,
then claims the event id in an in-process idempotency ledger, so a retry costs nothing instead of
paying for a second inference. The event becomes a generated incident id, and the machine route and
the human console both submit identical models through one analysis function.

Nemotron answers through a pinned tool call. Pydantic validates the payload; an out-of-enum severity
or a missing field is a provider error, not a graceful guess. Only the tool arguments are read: free
text and the reasoning field never reach the browser.

Sentinel's policy then decides, in code: high or critical sets requires_approval. The state machine
records approval_requested and waits. Executing early returns 409 approval_required and appends
execution_blocked — the point of the product, not a limitation. After approval the
chosen action runs from a closed catalog and the verifier compares simulated metrics against its
recovery condition, recording verified or failed. Seven audit lines later on the console path, eight
on the machine path, the trail shows what happened, who acted and what was never executed. Re-running
the identical event returns 200, duplicate true, the same incident id, in tens of milliseconds.
```

## NVIDIA usage

```
Inference runs on NVIDIA Build through its OpenAI-compatible endpoint. The model is
nvidia/nemotron-3.5-lightning-30b-a3b, supplied only as the NVIDIA_MODEL environment variable —
there is no default, so a deployment that cannot name its model cannot start an analysis. Requests
use temperature 0.1, top_p 0.9, a 4096-token ceiling and a pinned tool_choice, with a 90-second read
timeout sized to the measured latency band rather than a guess. Sentinel depends on the model for
what a runbook cannot do: read an ambiguous symptom description plus three evidence lines and commit
to a severity, causes and next actions. The demo showed the producer's own understated hint of
warning overridden as high, which is the value of the call. Reasoning is NVIDIA's; the decision
boundary is ours.
```

## Technical implementation

```
Python 3.13, FastAPI and pydantic 2, with httpx as the only network client and no framework in
front of the agent — no LangGraph, no AutoGen, no queue, no database. Seven modules: `schemas`,
`nvidia`, `analysis`, `workflow`, `simulation`, `ingestion` and `api` — the approval policy lives in
`analysis.py` and the provider config in `nvidia.py`. The console is three
static files served by the same process, with no build step, no bundler and no CDN, which is what
lets one CSP header on the root response lock the page to its own assets.

212 pytest tests pass in under a second, covering the bearer guard, idempotency claims and releases,
the gate's refusal order, the state machine, policy, provider-error mapping and the console's
rendered markup. A regression test asserts that no credential-shaped string reaches the shipped
files. The image is python:3.13-slim, 246 MB, running as UID 10001 with no root. One container, one
replica: workflow state and the idempotency ledger are per-process dicts bounded at 200 entries, and
the API answers 503 rather than silently evicting live work. Deployed on Coolify behind
sentinel.novatechsystem.co.uk.
```

## Impact

```
The useful thing here is not that a model can rate an incident; it is that a rated incident can be
handed to a human with the reasoning already structured, the gate already closed and the trail
already written. That combination is what an operational team can actually adopt: an agent that
compresses the first minute of triage without taking the decision that belongs to a person. The
machine route makes it fit an existing monitoring stack, since a producer needs one event and one
token rather than a new interface. The repository is MIT-licensed, self-contained and reproducible:
clone it, export two variables, run one container, and the full loop from producer event to verified
outcome plus replay is demonstrable in about fifteen seconds of wall clock.
```

## What is real vs simulated

```
REAL — machine event ingestion over a bearer-protected route, with in-process idempotency.
REAL — NVIDIA Nemotron assessment (severity, causes, recommended actions, confidence, rationale).
REAL — deterministic approval policy: high/critical always gates, and the model cannot lower it.
REAL — approval state machine: approve, reject, and a 409 refusal when execution is attempted early.
REAL — audit trail: append-ordered events with actor and timestamp, seven on the console path and
eight when a machine event opened the incident, including the refusals.
SIMULATED — remediation execution: a closed two-action catalog, every entry marked executes: false.
SIMULATED — verification: deterministic before/after metric snapshots, not a measurement of anything.
SIMULATED — incident existence itself: no service is scaled, restarted or repaired.
NOT IMPLEMENTED — LEARN: no memory across incidents, no model updates, no policy refinement.
```

## Known limitations

```
State is in-memory and bounded at 200 incidents and 200 events, so a restart ends every incident and
forgets which producer events were already handled. One replica is required, not preferred: a second
process is a second store, where a replay can create a duplicate incident and an approval can land
somewhere that never saw the incident. Authentication covers one route; the public console and the
analysis endpoint are intentionally unauthenticated, so anyone who can reach the port can pay for an
inference and approve their own incident, and every actor is recorded as operator. There is no rate
limiting. Inference is synchronous and takes 7–47 seconds measured, with no queue or streaming.
Remediation and verification are simulated, so "verified" means a catalog outcome met its recovery
condition, not that a symptom cleared. The NovaOps event contract is a design reference and a demo
emitter, not a wired integration. These are scope lines for this slice, stated rather than implied.
```

## Links

```
Live demo:      https://sentinel.novatechsystem.co.uk          (unauthenticated console, no login)
Demo video:     https://youtu.be/bQLiWO1G5Mw                   (2:29, YouTube unlisted, no login)
Health check:   https://sentinel.novatechsystem.co.uk/health
API docs:       https://sentinel.novatechsystem.co.uk/docs
Repository:     https://github.com/novatechsystemsgroup/novabrain-sentinel   (public, MIT)
Demo scenario:  docs/submission/demo-scenario.md
Evidence:       docs/submission/evidence-matrix.md
```

## Measured word counts

| Section | Words | §12 budget | Status |
|---|---|---|---|
| Project name | **2** | — | paste as-is |
| One-sentence tagline | **24** | — | paste as-is |
| Problem | **120** | 80–120 | within |
| Solution | **149** | 120–180 | within |
| How it works | **220** | 150–220 | within |
| NVIDIA usage | **122** | 100–150 | within |
| Technical implementation | **180** | 150–220 | within |
| Impact | **127** | 100–150 | within |
| What is real vs simulated | **131** | — | paste as-is |
| Known limitations | **160** | — | paste as-is |
| Links | **30** | — | paste as-is |

_(counts from `len(block.split())` on the fenced text; the brief's ranges are prose budgets, and every
bounded section is inside them.)_

_Re-measured on 2026-09-29 after the demo video line was added to the Links block: it went from 22 to
**30** words. Every other section above is unchanged from the TASK-015 measurement, and the seven
bounded prose sections are still inside the brief's ranges._
