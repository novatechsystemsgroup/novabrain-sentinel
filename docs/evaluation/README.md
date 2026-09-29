# Evaluation

Methodology, metrics and results for NovaBrain Sentinel.

## Live inference verification — TASK-011 (2026-09-28)

The first real model run through the shipped artifact. No mocked transport was involved.

| | |
|---|---|
| Image | `novabrain-sentinel:task011` (`docker build` of `main`, non-root UID 10001) |
| Provider | NVIDIA Build, `https://integrate.api.nvidia.com/v1/chat/completions` |
| Model | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| Secret handling | `NVIDIA_API_KEY` injected with `docker run -e` from the shell at run time; never written to disk, never printed |
| Endpoint | `POST /api/v1/incidents/analyze` |
| Input | the brief's example event: `source=novaops`, `title="API latency spike"`, p95 180 ms → 2.4 s, evidence `error rate 8.2%`, `CPU 91%`, `severity_hint=unknown` |

### Results

| Run | `incident_id` | Wall clock | Severity | Confidence | `requires_approval` |
|---|---|---|---|---|---|
| 1 | `inc_0b86102788ac4420bbeae77574c1a1d2` | 12.8 s | `high` | 0.87 | `true` |
| 2 | `inc_1bec63cbae3049ebb0275150a6766c9a` | 47.1 s | `high` | 0.87 | `true` |

Both runs returned HTTP 200 with the full normalised shape
(`incident_id`, `status`, `assessment`, `model`) and all seven assessment fields populated.

Run 1 `reasoning_summary`: *"The combination of sharply increased latency, elevated error
rate, and near-capacity CPU usage indicates a high-impact incident requiring immediate
attention."* — one sentence, a rationale rather than a trace.

### Checks performed on the raw response bodies

- No `reasoning_content` field, and no chain-of-thought text, in either response.
- `severity_hint=unknown` did not anchor the classification: the model raised it to `high`
  from the evidence, which is the behaviour the system prompt asks for.
- The model volunteered `requires_approval=true`; the Sentinel floor would have set it anyway
  for a `high` incident.
- Container log shows `POST /api/v1/incidents/analyze 200 OK` and nothing resembling a key.
- `GET /health` and `GET /` were re-checked against the same image and are unchanged.

### What this tells us

Latency is bimodal for a reasoning model: the same input produced 12.8 s and 47.1 s. A
single-sample benchmark would be misleading, so budget for the tail (`READ_TIMEOUT = 90 s`)
and report ranges. Assessment *quality* was stable across runs; only phrasing and the number
of actions differed.

## Approval-gate verification — TASK-012 (2026-09-28)

> **Real NVIDIA inference + simulated execution and verification — not real remediation.**
> The assessment in this run came from `nvidia/nemotron-3.5-lightning-30b-a3b` over the real
> provider. Everything from `execute` onward was simulated inside the process; no service was
> restarted, no replica was created, no infrastructure was touched.

The whole loop — `OBSERVE → UNDERSTAND → DECIDE → REQUEST APPROVAL → ACT (simulated) →
VERIFY (simulated)` — was driven through one HTTP client against the built image, so each
stage is checked as the operator meets it rather than as a unit test.

| | |
|---|---|
| Artifact | `docker build` of the working tree, run as `sentinel-task012:smoke` on `127.0.0.1:8013`, non-root UID 10001, one worker |
| Provider | NVIDIA Build, live. `NVIDIA_API_KEY` injected with `docker run -e` at run time only |
| Input | `source=novaops`, p95 2.4 s under 91 % CPU, evidence `p95_latency_ms=2400`, `cpu_percent=91`, `error_rate_percent=8.2`, `deploy v2026.09.3`, `severity_hint=high` |
| Script | the 9-step walk below; transient, kept outside the repository |

### Path A — approve, then execute

| Step | Request | Result |
|---|---|---|
| 1 | `POST /api/v1/incidents/analyze` | `200` in **15.2 s** → `inc_ae3dc4898d774d938d1b7053d796ba8a`, `severity: high`, `confidence: 0.92`, `requires_approval: true`, state `awaiting_approval` |
| 2 | `POST …/execute` `{"action":"scale_api_replicas"}` | **`409 approval_required`** — "This incident is awaiting an operator approval." |
| 3 | `POST …/approve` with a note | `200` → state `approved`, `approval.actor: "operator"` |
| 4 | `POST …/execute` the same action | `200` → state `verified`, `verification.simulated: true`, `success: true` |
| 5 | `POST …/execute` again (`restart_api_service`) | **`409 already_executed`** — a finished incident is closed |
| 6 | `GET …/{incident_id}` | `200` → event + assessment + state + decision + action + verification + 8-event trail |

Step 2 before step 3 is the requirement under test: the gate refused execution *and* recorded
the attempt. Steps 2 and 5 are the two distinct refusals the state machine makes, and both
answered `409`, not `403`, leaving `403` free for the authentication layer this slice does not
have yet.

### Path B — reject, and the veto is permanent

| Step | Request | Result |
|---|---|---|
| 1 | `POST /api/v1/incidents/analyze` (different title) | `200` in **19.3 s** → `inc_310a1d21a0a74813926022cbc877125f`, `awaiting_approval` |
| 2 | `POST …/reject` `"Hold; change freeze."` | `200` → state `rejected` |
| 3 | `POST …/approve` | **`409 invalid_transition`** — "Cannot approve an incident in state 'rejected'." |
| 4 | `POST …/execute` | **`409 approval_rejected`** — "This incident was rejected. A rejection is permanent." |

A rejected incident cannot be re-approved, so the rejection is not a delay but a dead end:
`rejected` has no outgoing edge in the state machine. Its trail is
`['incident_analyzed', 'approval_requested', 'approval_rejected', 'execution_blocked']`.

### The audit trail as it came back

Append order is the authoritative sequence. These timestamps are real; `execution_finished` and
`verification_recorded` came out 4 µs apart, which is a gap the design does not rely on:
neighbouring events can share a timestamp, so the list is read in order and never sorted:

```
2026-09-28T18:49:55.710578+00:00  incident_analyzed      sentinel {"severity":"high","confidence":0.92,"requires_approval":true,"model":"nvidia/nemotron-3.5-lightning-30b-a3b"}
2026-09-28T18:49:55.710785+00:00  approval_requested     sentinel {"severity":"high","reason":"Sentinel approval policy requires an operator decision."}
2026-09-28T18:49:55.731204+00:00  execution_blocked      operator {"action":"scale_api_replicas","reason":"approval_required"}
2026-09-28T18:49:55.734057+00:00  approval_granted       operator {"note":"Approved for simulated scale-out on the demo cluster."}
2026-09-28T18:49:55.735724+00:00  execution_requested    operator {"action":"scale_api_replicas","mode":"simulated","note":"simulated only"}
2026-09-28T18:49:55.735797+00:00  execution_finished     sentinel {"action":"scale_api_replicas","state":"verified"}
2026-09-28T18:49:55.735801+00:00  verification_recorded  sentinel {"status":"verified","success":true,"simulated":true}
2026-09-28T18:49:55.737154+00:00  execution_blocked      operator {"action":"restart_api_service","reason":"already_executed"}
```

`sentinel` wrote the observation, the policy outcome and the machine's own bookkeeping;
`operator` wrote every human intent — including the premature execution attempt. The client
confirmed `timestamps == sorted(timestamps)`.

Note the shape of the wall clock: 15.2 s of provider latency is followed by sub-30 ms for the
entire workflow, because approval and execution are in-process operations against a dictionary.
That is the direct consequence of the no-database decision, and the reason single-replica is a
hard requirement rather than a preference.

### The simulated verification, verbatim

```json
{
  "status": "verified",
  "simulated": true,
  "before": { "api_replicas": 2, "p95_latency_ms": 2400, "error_rate_percent": 8.2, "service_restarts": 0 },
  "after":  { "api_replicas": 4, "p95_latency_ms": 610,  "error_rate_percent": 0.4, "service_restarts": 0 },
  "success": true
}
```

Both snapshots are constants from `sentinel/simulation.py`: `before` is the fixed `DEGRADED`
baseline the simulator pretends to observe, `after` is the catalog entry's `SCALED` result.
They matched this incident's evidence (`p95_latency_ms=2400`, `error_rate_percent=8.2`) because
the run's input was authored to match, not because anything was measured. No metric was read.

### Guard rails checked on the same run

- `POST …/execute {"action":"rm_-rf_production"}` → **`422`** `literal_error`, "Input should be
  'scale_api_replicas' or 'restart_api_service'". The pydantic enum rejected it before the
  store was opened, so no state changed and no audit event was written.
- `GET /api/v1/incidents/inc_does_not_exist` → `404 incident_not_found`, naming the id only.
- Leak scan across every response body the service produced: the NVIDIA key prefix absent,
  `reasoning_content` absent, and the provider base URL absent. The trail carries the model *name*,
  which is safe to show, and never the provider's raw payload.
- `GET /` and `GET /health` re-checked against the same image; the TASK-011 analysis response
  is byte-compatible with its documented shape.

## Console walkthrough — TASK-013 (2026-09-28)

> **Real NVIDIA inference + simulated execution and verification — not real remediation.**

The same loop was driven a second time, but through the browser at `GET /` instead of an HTTP
client, to check the operator-facing claims rather than the API ones: that a judge can reach a
verdict in four clicks, that the gate is visible before it is crossed, and that nothing in the
page invents a number the backend did not return.

| | |
|---|---|
| Artifact | `docker build` of the working tree (`sha256:c1c2ea7a…`), run as `sentinel-console` on `127.0.0.1:8022`, non-root UID 10001, one worker |
| Provider | NVIDIA Build, live. `NVIDIA_API_KEY` injected with `docker run -e NAME` at run time only |
| Input | the prefilled demo incident: `source=novaops`, `title="API latency spike"`, `severity_hint=unknown`, evidence `error rate increased to 8.2 %`, `CPU increased to 91 %` |
| Viewports | 1440 × 900 and 390 × 844 |

### Timings

One run was timed from the click handler to the first audit event, so the number is the
provider's, not a polling artefact:

| Measurement | Value |
|---|---|
| Run click → `incident_analyzed` | **13.17 s** (`20:02:35.240` → `20:02:48.413`) |
| Run click → `incident_analyzed`, second console run at 390 px | ≈ 11 s (click noted to the nearest second) |
| `incident_analyzed` → `approval_requested` | 0.19 ms |
| `execution_requested` → `execution_finished` | 3.56 ms |
| `execution_finished` → `verification_recorded` | 0.02 ms |
| Whole workflow after the model answers | under 4 ms |

Both console runs sit in the 11–13 s band, which is inside the 12.8–47.1 s range TASK-011
measured for the same input and the same model. The UI adds nothing measurable; the wait is the
provider's. The two human pauses in the trail (139.6 s to read and approve, 12.1 s to request
execution) are the operator, and they are recorded as such.

### Path taken at 390 px, then repeated at 1440 px

| Step | What the operator does | What the page showed |
|---|---|---|
| 1 | *Run Demo Incident* | Real elapsed seconds, no percentage, assessment panel left reading "No assessment yet." |
| 2 | read the assessment | `severity: high`, `confidence: 0.87`, `requires_approval: true`, model name, and a one-sentence rationale |
| 3 | *Attempt Execution* (before approving) | **`409`** rendered as "Execution blocked by Sentinel policy — approval is required before this action can run.", and the attempt written to the trail as `execution_blocked` / `operator` |
| 4 | *Approve*, then *Execute simulated action* | state `verified`, `Simulation: YES · simulated`, before/after metrics, every action button disabled |

The 1440 px run ended with a 7-event trail in append order:
`incident_analyzed → approval_requested → execution_blocked → approval_granted →
execution_requested → execution_finished → verification_recorded`. The 390 px run produced the
same shape without the premature attempt.

### Claims checked against the rendered DOM

- The before/after figures on screen (`2 → 4`, `2400 → 610`, `8.2 → 0.4`, `0 → 0`) are the
  backend's `verification` object verbatim. `renderVerification` reads
  `verification.before[key]` and `verification.after[key]` for every row; the only literals it
  holds are display labels. The `8.2 %` / `91 %` that do appear in `static/app.js` are the
  prefilled demo incident's evidence text, on the input side of the loop.
- `severity_hint=unknown` was again raised to `high` by the model, so the prefilled hint is not
  steering the result.
- Scan of `document.documentElement.outerHTML` after a full run: the NVIDIA key prefix,
  `integrate.api.nvidia.com`, `reasoning_content`, `api_key`, `NVIDIA_API_KEY` and `Bearer ` all
  occur **0** times.
- The page loads exactly one script and one stylesheet, both same-origin under `/static/`, with
  no inline script, no inline handler and no off-origin subresource.
- CSP is present on `GET /` and absent on `/api/*` and `/static/*`, as designed. Note that
  `HEAD /` answers `405` because only `GET` is routed — check headers with `curl -s -D -`, not
  `curl -I`.
- Panels stack in loop order (`OBSERVE → UNDERSTAND → DECIDE → ACT → VERIFY → AUDIT`) at 390 px;
  at 1440 px the two-column pairing is unchanged.
- `GET /health` is byte-identical to the TASK-011 shape; the container still runs as UID 10001.

### Browser console

One error across the whole session, and it is Chrome's own network log:
`Failed to load resource: the server responded with a status of 409 (Conflict)` for the
deliberate pre-approval execution in step 3. Zero JavaScript errors, zero warnings. Any non-2xx
fetch produces that line, so it cannot be removed without hiding the safety behaviour the demo
exists to show.

## Machine ingestion verification — TASK-014 (2026-09-28)

> **Real NVIDIA inference + safe simulated remediation — not real remediation.**
> The event arrived over `POST /api/v1/events/ingest` from a machine-shaped client, the
> assessment came from `nvidia/nemotron-3.5-lightning-30b-a3b` over the live provider, and the
> approval gate was crossed by a human in the browser. Only `execute` onward is simulated: no
> service restarted, no replica was created, no metric was read.

| | |
|---|---|
| Artifact | `docker build` of the working tree (`sha256:cff97d15…`), run as `sentinel-task014` on `127.0.0.1:8024`, non-root UID 10001, one worker |
| Provider | NVIDIA Build, live. `NVIDIA_API_KEY` injected with `docker run -e NAME` at run time only |
| Ingest secret | `SENTINEL_INGEST_TOKEN` — 64 hex chars generated into a `0600` file outside the repo, passed with `--env-file`, never a CLI argument, never printed, never committed |
| Model | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| Viewports | 1440 × 900 and 390 × 844 |

### The ingest loop, timed against the live provider

| Case | Request | Result |
|---|---|---|
| first touch | `POST /api/v1/events/ingest` `event_id=novaops-e2e-0001` | **`201`** in **11.65 s** → `inc_35ecc84dc5234720b7a8917035e7c7f7`, `workflow_state: awaiting_approval`, `duplicate: false`, relative `console_path`, `Location` header on the same path |
| replay | the same bytes, same `event_id` | **`200`** in **13.3 ms** → identical `incident_id`, `duplicate: true`, the same five keys |
| producer race | two concurrent posts, `event_id=novaops-race-0001` | winner **`201`** in **15.85 s**; loser **`409 event_in_progress`** in **64 ms**, while the winner was still inside inference |
| replay after the winner | same `event_id` again | **`200`** in **18.5 ms**, same `incident_id`, `duplicate: true` |
| through the emitter | `scripts/send_demo_event.py --event-id novaops-emitter-0001` | **`HTTP 201`** in **21.0 s** → `inc_1f364ed674cd487fba3377c07d0ef921`, then `HTTP 200 / duplicate: True` for the same id in **0.31 s** (process start, not provider) |
| no token | `POST …/ingest` with `{}` body, no header | **`401`** |
| wrong token | `POST …/ingest` with `{}` body, `Bearer` a wrong value | **`401`** + `www-authenticate: Bearer` — **not** `422`, so the secret was checked before the body was parsed |
| unauthenticated analyse (unchanged) | `POST /api/v1/incidents/analyze` | `200` in **5.60 s**, keys `incident_id` / `status` / `assessment` / `model` |

One inference per `event_id`, and the two replays cost 13–18 ms: the replay guard answers from
memory and never reaches the provider. The loser of the race got a `409` rather than a second
incident, so the concurrency case is a refusal, not a silent double-charge.

### The model decided severity, not the producer

Three machine events, three different hints, one assessment band — the alias map is a
normalisation, never an escalation:

| `severity_hint` sent | stored hint | model `severity` | `confidence` | `requires_approval` |
|---|---|---|---|---|
| `warning` | `medium` | `high` | 0.87 | `true` |
| *(emitter default)* `warning` | `medium` | `high` | 0.87 | `true` |
| `critical` | `critical` | `high` | 0.87 | `true` |

`warning → medium` and `critical → critical` applied as documented; `APPROVAL_FLOOR` then set
`requires_approval` for a `high` incident regardless of what the model opined.

### The audit trail as it came back

Append order is authoritative, so note that `event_ingested` is stamped `22:11:45` while its own
`details.observed_at` reads `14:12:03` — the authored observation time is carried as data and is
never used to reorder the trail:

```
2026-09-28T22:11:45.539401+00:00  event_ingested         sentinel  {"event_id":"novaops-e2e-0001","source":"novaops","event_type":"high_cpu","observed_at":"2026-09-28T14:12:03+00:00","received_at":"2026-09-28T22:11:33.917883+00:00"}
2026-09-28T22:11:45.539552+00:00  incident_analyzed      sentinel  {"severity":"high","confidence":0.87,"requires_approval":true,"model":"nvidia/nemotron-3.5-lightning-30b-a3b"}
2026-09-28T22:11:45.539564+00:00  approval_requested     sentinel  {"severity":"high","reason":"Sentinel approval policy requires an operator decision."}
2026-09-28T22:12:32.610670+00:00  execution_blocked      operator  {"action":"scale_api_replicas","reason":"approval_required"}
2026-09-28T22:12:42.835470+00:00  approval_granted       operator  {"note":"Approved from Sentinel console."}
2026-09-28T22:12:51.534092+00:00  execution_requested    operator  {"action":"scale_api_replicas","mode":"simulated","note":"Executed from Sentinel hackathon console."}
2026-09-28T22:12:51.534568+00:00  execution_finished     sentinel  {"action":"scale_api_replicas","state":"verified"}
2026-09-28T22:12:51.534593+00:00  verification_recorded  sentinel  {"status":"verified","success":true,"simulated":true}
```

The machine opened the record; the operator wrote every human intent, including the premature
execution attempt. Three gaps in wall-clock terms — 47 s to read the assessment, 10 s to approve,
9 s to request execution — are the human, and the workflow itself took 0.5 ms after the model
answered.

### Console walk via `/?incident=<id>`

| Step | What the operator does | What the page showed |
|---|---|---|
| 1 | paste the `console_path` from the `201` | header `Incident inc_35ecc84d…`, `Workflow awaiting_approval`, all six panels populated from one same-origin `GET` — no re-analysis, no second incident |
| 2 | read the trail | first entry labelled **"Operational event ingested"**, with `event_id · source · event_type · observed_at · received_at` beneath it |
| 3 | *Attempt Execution* before approving | **`409`** rendered as "Execution blocked by Sentinel policy — Approval is required before this action can run.", plus the `execution_blocked` row above |
| 4 | *Approve* | "Operator approved — Approved. The gate is open for a simulated action.", `approval_granted` in the trail |
| 5 | *Execute simulated action* | state `verified`, `RESULT VERIFIED`, `SIMULATION YES · simulated`, before/after `2 → 4`, `2400 → 610`, `8.2 → 0.4`, `0 → 0` |
| 6 | *Clear / New Incident* | `location.search` empty, still `/`, incident header gone, and no navigation occurred (`history.replaceState`) |

The emitter's second incident (`inc_1f364ed6…`) was opened the same way at 1440 × 900 and 390 × 844
and produced the identical panel set, so the bridge is not tied to one record.

### Claims checked against the rendered DOM and the network log

- Subresource list for the whole session: `/static/styles.css`, `/static/app.js`, `/health`, and
  `/api/v1/incidents/...` only — **zero** off-origin requests, and none of them carry an
  `Authorization` header.
- `document.documentElement.outerHTML` after the full walk: `Bearer`, `SENTINEL_INGEST_TOKEN`,
  the NVIDIA key prefix and any 64-hex token-shaped string occur **0** times. The ingest secret
  never reaches the browser.
- `/?incident=../../etc/passwd` → the id fails `INCIDENT_ID_PATTERN`, so **no API request is
  issued at all** and the page shows "Incident not found — This incident is not a known workflow
  record or it has left memory after a restart." The query parameter cannot address anything
  other than a same-origin incident.
- Horizontal overflow at 390 px: **0 px**. Panels still stack in loop order, and the ACT chip
  still reads `Approval: REAL · Action: SIMULATED` — TASK-013A's attribution survived the new
  entry point.
- The before/after figures on screen are the backend `verification` object verbatim; the run
  returned `{"status":"verified","simulated":true,"success":true}` with the catalog constants.
- No `reasoning_content` and no chain-of-thought text appeared in any response body or in the DOM.
- Browser console: one line, Chrome's own `Failed to load resource: 409 (Conflict)` for the
  deliberate step-3 refusal. Zero JavaScript errors, zero warnings.

### What this tells us

11.65–21.0 s for a machine-triggered analysis is the same band TASK-011 and TASK-013 measured for
the manual route, which is expected: ingestion adds a dictionary reservation and an audit append,
not a second model call. The endpoint is honest about being synchronous — a producer must budget
at least the 90 s read timeout, and the two-replica limit still applies because both the workflow
store and the idempotency ledger are per-process memory that a restart empties.

## Submission QA — TASK-015 (2026-09-28)

> **Real NVIDIA inference + safe simulated remediation — not real remediation.**

Two runs, chosen to cover the two doors the submission claims: the public production URL reached
from a browser, and the canonical machine-first event reached from `scripts/send_demo_event.py`.
The purpose was to confirm the documented numbers still hold on the tree being submitted, not to
add features.

| | |
|---|---|
| Production | `https://sentinel.novatechsystem.co.uk`, one replica, console-driven run at `GET /` |
| Local artifact | `docker build` of the working tree (`sha256:43043023…`), tag `novabrain-sentinel:task015`, 246 MB, run on `127.0.0.1:8025`, non-root UID 10001, healthcheck `healthy`, `RestartCount: 0` |
| Provider | NVIDIA Build, live, `nvidia/nemotron-3.5-lightning-30b-a3b`; keys injected with `docker run -e NAME` at run time only |
| Viewports | 1440 × 900 and 390 × 844 |

### Timings

| Measurement | Value |
|---|---|
| Production: *Run Demo Incident* click → `incident_analyzed` | **6.65 s** (`22:52:35.49` → `22:52:42.140992`) |
| Production: `incident_analyzed` → `approval_requested` | 0.11 ms |
| Local: `POST /api/v1/events/ingest` wall time (201) | **9.6 s** |
| Local: replay of the same `event_id` (200, `duplicate: true`) | **0.02 s**, no second inference |
| Local: whole workflow after the model answers, 5 audit appends | 164 ms (`22:47:54.465438` → `22:47:54.629636`) |

The production run is the fastest end-to-end analysis measured on this project, so the documented
band is revised from `12.8–47.1 s` to **6.7–47.1 s** across the six live runs (TASK-011: 12.8 and
47.1 s; TASK-012: 19.3 s; TASK-013: 11 and 13.17 s; TASK-014: 11.65–21.0 s; TASK-015: 6.65 s
production, 9.6 s machine-triggered). The `90 s` read timeout still clears the slow tail, and the
`7–47 s` wording now used in the README and the architecture docs is that range rounded.

### Canonical machine-first flow, local container

`scripts/send_demo_event.py` posted `event_id: task015-evt-20260928T224744Z` with `source=novaops`,
`event_type=ram_high`, `severity_hint=warning` and the three evidence lines:

1. `HTTP 201`, `incident_id: inc_2f5ff8a508cc4af199c840b28521c61f`, `workflow_state: awaiting_approval`,
   `duplicate: false`, `console_path: /?incident=inc_…`.
2. The workflow record: `severity high | confidence 0.86 | requires_approval True`, model
   `nvidia/nemotron-3.5-lightning-30b-a3b`, 3 likely causes, 4 recommended actions, and
   `has reasoning_content? False`.
3. Execution attempted before approval → `409 {"detail":{"error":"approval_required",…}}`.
4. `approve` → `200 state approved`; `execute scale_api_replicas` → `200 state verified` with
   `{"status":"verified","simulated":true,…,"success":true}` and the catalog constants
   (`2 → 4` replicas, `2400 → 610` ms, `8.2 → 0.4` %, `0 → 0` restarts).
5. Eight audit events in append order, starting with `event_ingested` and carrying
   `execution_blocked` between `approval_requested` and `approval_granted`.
6. Replaying the same `event_id` → `HTTP 200 in 0.02s`, `duplicate: True`, the **same**
   `incident_id`, `workflow_state: verified`.
7. A request with no token → `401 {"detail":{"error":"invalid_ingest_token",…}}` with
   `www-authenticate: Bearer`.

Opening the returned `console_path` in a browser rendered the incident with
"Operational event ingested" as the first trail row, proving the producer → console bridge.
The page shows human-readable labels (`Operational event ingested`); the raw audit names
(`event_ingested`) are in the API JSON — both are correct, and a demo frame that needs the raw
token has to come from a terminal, not the console.

### Public production QA

`GET /` 200 (0.177 s, 9 524 B), `/health` 200 (46 B), `/docs` 200, `/openapi.json` 200 (10 960 B),
`GET /api/v1/events/ingest` 405, `POST` without a token 401, `POST` with a wrong token 401.
The strict CSP is present on `GET /` only. One real inference produced
`inc_0a0d3648688244a4ac37a1763272cbd7` → `high` / `0.87` / `requires_approval true`; the deliberate
pre-approval attempt returned 409 and was audited; approve → execute → `verified`; the trail held
seven events. Re-checking the rendered page afterwards: `Workflow verified`,
`nvidia · nvidia/nemotron-3.5-lightning-30b-a3b`, the permanent disclosure
"Real NVIDIA inference · Safe simulated remediation", `scrollWidth − clientWidth = 0` at both
1440 px and 390 px, and **0 occurrences** for each of the eight probes: the NVIDIA key prefix
(the prefix string exists in this repository only as a test assertion and as a scan description,
never followed by a value — `docs/submission/security-check.md`), `integrate.api.nvidia.com`,
`reasoning_content`, `api_key`, `NVIDIA_API_KEY`, `SENTINEL_INGEST_TOKEN`, a `Bearer ` header,
and `authorization`.

The browser console for the whole production session held exactly one line: Chrome's own
`Failed to load resource: 409 (Conflict)` for the deliberate blocked attempt. Zero JavaScript
errors, zero warnings — the same result as TASK-013 and TASK-014, and the same reason: any non-2xx
fetch produces that line.

### Not proven on production

The `201`/replay pair was **not** exercised against the public URL. `SENTINEL_INGEST_TOKEN` is a
runtime-only value that this QA pass cannot read, so an unauthenticated probe can prove the guard
rejects (verified: 401 twice) but not that the guard accepts. The full machine-first loop above is
therefore evidence from the local container built from the same tree, and the check-list item stays
`MANUAL ACTION REQUIRED` rather than `PASS`.

`/openapi.json` does not document the bearer requirement on `/api/v1/events/ingest` — zero
occurrences of `Bearer` in the schema. Fixing it means editing `api.py`, which would require a
redeploy to verify; TASK-015 §0 forbids changes that do not unblock the submission, so this is
recorded as a known limitation instead, and the contract is documented in
[`docs/architecture/machine-event-ingestion.md`](../architecture/machine-event-ingestion.md).

## Not yet measured

`LEARN` is not implemented, so there is nothing to evaluate for it.

Machine ingestion has not produced a `201` on the **public** URL — see *Not proven on production*
above. It needs the deployed runtime token, which this QA pass deliberately does not read.

The `failed` verification path is deterministic and covered by tests (`restart_api_service` on
a `critical` incident does not recover it, so `state: "failed"` and `after == before`), but it
has not been exercised against a live model, because a live `critical` assessment is not
something the run can order the model to produce.

Real remediation is out of scope by design: nothing here measures whether a scale-out actually
fixes a latency spike. `verification.success` means "the simulated action's catalog outcome met
its recovery condition", not "the incident is resolved".
