# Judge Quickstart — NovaBrain Sentinel

A reviewer-facing path through the entry: what it is, which URL to open, what to click, what the
page should show, and which half of it is real. Everything below is testable in one browser tab in
about 90 seconds — no curl, no Postman, no API token, no local setup, no Docker, no `git clone`.

| | |
|---|---|
| **Live demo** | <https://sentinel.novatechsystem.co.uk> — no login |
| **Source** | <https://github.com/novatechsystemsgroup/novabrain-sentinel> (MIT, public) |
| **Model** | `nvidia/nemotron-3.5-lightning-30b-a3b` on NVIDIA Build (`https://integrate.api.nvidia.com/v1`) |
| **Demo video** | <https://youtu.be/bQLiWO1G5Mw> — 2:29, YouTube, unlisted, no login |
| **Health** | <https://sentinel.novatechsystem.co.uk/health> |

## The 30-second summary

Sentinel is an **event-driven operational agent**, not an incident chatbot. Nobody types a question
and reads prose back. One operational event arrives — from a machine producer over HTTP, or from
the console form — a live NVIDIA Nemotron call returns a **schema-validated structured assessment**
(severity, confidence, likely causes, recommended actions, concise rationale), and Sentinel's own
**deterministic policy in code** decides whether a human is required before anything can act.
Every step, including the attempts the policy refused, is appended to an audit trail.

- **REAL:** event submission, the NVIDIA inference call, the structured assessment, the
  high/critical approval gate, the refusal of an unapproved execution, the audit trail.
- **SIMULATED:** the remediation itself and its before/after metrics. No service is restarted and
  nothing is scaled. The console says so on screen, in three separate places.
- **NOT IMPLEMENTED:** `LEARN` — no memory, no feedback into assessment, no model updates. The
  stage is labelled *not implemented* on the page rather than quietly omitted.

The one design claim worth checking first: **the model supplies judgement, the code supplies the
safety.** `high` and `critical` always require an operator, and the model can add that requirement
but can never remove it.

## Test it in 90 seconds (browser only)

Open <https://sentinel.novatechsystem.co.uk>. Panel 1 arrives pre-filled with the canonical demo
incident — leave it exactly as it is.

1. **Check the header.** `NovaBrain Sentinel`, subtitle *Event-driven operational agent*, and
   `Status: ONLINE` a moment after load (the dot is the result of a real `/health` poll).
2. **Read the loop strip.** `OBSERVE → UNDERSTAND → DECIDE` are marked *real*;
   `ACT / REQUEST APPROVAL` is split into `Approval: REAL · Action: SIMULATED`; `VERIFY` is marked
   *simulated*; `LEARN · not implemented`. That strip is the entry's honesty claim in one glance.
3. **Press `Run Demo Incident`.** The run bar reads *"NVIDIA Nemotron is assessing the incident
   (allow up to 90s)"* and counts real elapsed seconds. Inference is genuinely remote: measured
   6.7–47.1 s across six live runs, with a 90-second read budget. Wait it out; nothing is faked
   behind a progress percentage.
4. **Read panel 2 `Understand · Assessment`.** Severity, Confidence, Model and *Requires approval*
   appear, plus a summary, likely causes, recommended actions and a short decision rationale. The
   model line should read `nvidia · nvidia/nemotron-3.5-lightning-30b-a3b`. Confidence is rendered
   as a rounded whole percentage (e.g. `86%`) and **varies between runs**. Every run of this
   incident recorded in [`docs/evaluation/README.md`](../evaluation/README.md) came back `high`, so
   that is what the gate is written for — but nothing here promises a particular severity or
   confidence on your run, and a different answer is not a defect.
5. **Now try to bypass the gate — before approving.** Go to panel 4 `Act · Remediation` and press
   `Attempt Execution`. Expect a warning band: **"Execution blocked by Sentinel policy"** —
   *Approval is required before this action can run.* Nothing ran. Panel 6 gains a line
   `Execution blocked by policy`, actor `operator`. This is the load-bearing test: the refusal is
   enforced in code and recorded, not worded in a prompt.
6. **Approve.** Panel 3 `Decide · Approval gate` shows `⚠ HUMAN APPROVAL REQUIRED` while the
   incident waits; press `Approve`. The gate records the decision, the actor, the note and the
   timestamp, and the run bar state changes to `approved`.
7. **Execute the remediation.** Panel 4 is labelled `SIMULATED ACTION` and states, under the
   buttons: *"Demo safety mode: execution and verification are simulated. Sentinel never touches a
   real service."* Pick `Scale API Replicas` from the *Action* dropdown and press
   `Execute simulated action`.
8. **Check what it claims to be.** Panel 5 `Verify · Outcome` shows Result `VERIFIED` and
   Simulation `YES · simulated`, with a deterministic before → after list:
   `API replicas: 2 → 4`, `p95 latency (ms): 2400 → 610`, `Error rate (%): 8.2 → 0.4`,
   `Service restarts: 0 → 0`. **This action is simulated.** Those four numbers are authored
   constants in `sentinel/simulation.py`, not measurements of anything; no orchestrator was called.
9. **Read the audit trail in panel 6 `Audit · Trail`, top to bottom.** Via this console path you
   should see **seven** entries, in append order:
   `Incident analyzed` → `Human approval requested` → `Execution blocked by policy` →
   `Operator approved` → `Simulated action requested` → `Simulated action finished` →
   `Outcome verified`.
   You will **not** see *"Operational event ingested"* — that event exists only on the
   machine-ingestion path below, where a producer posts an event over HTTP. The console path is
   deliberately not credited with ingestion metadata it did not receive.
10. **Optional: the other terminal outcome.** Press `Clear / New Incident` and run again. If an
    assessment comes back `critical`, choosing `Restart API Service` verifies as `FAILED` with the
    metrics unchanged — both outcomes are reachable deterministically, without randomness. Note
    that `Clear / New Incident` resets only the browser view; incidents stay in the running
    container's memory.

**If the assessment comes back `low` or `medium`:** no approval is required, `Attempt Execution`
stays disabled and `Execute simulated action` is enabled straight away. That is the same policy
working in the other direction, not a failure — run the incident again if you want to see the gate.

## The machine-to-machine path (needs your own token)

`POST /api/v1/events/ingest` is the primary entry point the console is a view onto. It is
**bearer-token protected**, and **the production token is not shared** — judges are not given a
secret to a system they did not deploy. What you can check against the live URL without any
credential is that the door is shut:

```bash
curl -s -i -X POST https://sentinel.novatechsystem.co.uk/api/v1/events/ingest \
  -H 'Content-Type: application/json' -d '{}' | head -n 8
# HTTP/2 401
# www-authenticate: Bearer
```

The guard runs **before the request body is parsed**, which is why an empty `{}` is refused with
`401` rather than `422`; `GET` on the same path returns `405`. If it is unset server-side, the
route answers `503 ingest_not_configured` instead of being left open.

To walk the full producer path, run your own instance (one `docker build`, three environment
variables) with a token you choose, then use the stdlib emitter:

```bash
.venv/bin/python scripts/send_demo_event.py --url http://127.0.0.1:8000 --event-id novaops-demo-0001
# 201 → incident_id, workflow_state awaiting_approval, console_path /?incident=<id>
# same event_id again → 200 duplicate:true, same incident_id, and no second model call
```

That whole sequence — producer command, `201`, the same incident opening in the browser through
`/?incident=<id>`, and the replay answering `duplicate: true` — is the part the demo walkthrough
films, so you can watch the machine path before you decide to run it yourself:
**<https://youtu.be/bQLiWO1G5Mw>** (2:29, YouTube unlisted, no login).

That path starts its audit trail one event earlier: `Operational event ingested` then
`Incident analyzed` — eight entries for a full loop instead of seven. The producer payload
(`source`, `event_type`, `title`, `description`, `severity_hint`, `evidence[]`) is a
**NovaOps-compatible producer contract**, not a NovaOps integration; NovaOps is a separate
repository and nothing is wired between them.

## What is real and what is simulated

| # | Behaviour | Status |
|---|---|---|
| 1 | Console submission of an incident | **Real** |
| 2 | Bearer-token HTTP ingestion of a machine event, with idempotent replay | **Real** |
| 3 | NVIDIA Nemotron inference over the network | **Real** |
| 4 | Severity, confidence, causes, recommendations, rationale (schema-validated) | **Real** |
| 5 | The approval requirement, decided by policy in code | **Real** |
| 6 | Refusing execution without approval — and auditing the refusal | **Real** |
| 7 | Approve / reject transitions, with actor, note and timestamp | **Real** |
| 8 | The ordered audit trail | **Real**, but per-process: nothing survives a restart |
| 9 | Running the remediation (scale / restart) | **Simulated** — no orchestrator is called |
| 10 | Before/after metrics and the verification verdict | **Simulated** — authored constants |

The project deliberately labels simulated behavior instead of presenting simulated infrastructure
effects as real.

## What proves this is more than an LLM wrapper

Ten checkable facts, all in the repository:

1. The model's answer is **forced into a tool call** (`submit_incident_assessment`, pinned
   `tool_choice`, `temperature 0.1`) and is read only from `tool_calls[0].function.arguments`, then
   validated by pydantic — so it cannot degrade into prose. `sentinel/nvidia.py:140-143`.
2. Free-form model text and reasoning output are never read, never stored, never rendered. Only the
   validated schema reaches the browser.
3. The approval floor is a set in code — `APPROVAL_FLOOR = frozenset({"high", "critical"})` — and
   the policy can **raise** `requires_approval` but never lower it. `sentinel/analysis.py:12-18`.
4. Execution requires `requires_approval is False` **or** `state == "approved"`, with the guards
   ordered already-executed → rejected → approval-required. `sentinel/workflow.py:70-83`.
5. A refusal is appended to the audit trail *before* the error is raised, so the trail records what
   did **not** happen and who asked. `sentinel/workflow.py:184-189`.
6. The action surface is closed: exactly two catalog entries; anything else is a `422` before the
   store sees it. `sentinel/simulation.py:32-51`.
7. `sentinel/simulation.py` declares `simulated: True` and `executes: False` on its own types — a
   greppable statement that this module performs no real work.
8. Ingestion compares the bearer token with `hmac.compare_digest` before parsing the body, and
   answers `401 invalid_ingest_token` + `WWW-Authenticate: Bearer`. `sentinel/ingestion.py:47-73`.
9. The idempotency ledger returns either the incident already made or a `409 event_in_progress` for
   a mid-flight duplicate, and refuses with `503` when full rather than dropping a claim — so a
   replay does **not** spend a second inference. `sentinel/ingestion.py:92-142`.
10. If inference throws, the claim is released and nothing is recorded, so a failed run leaves no
    phantom incident. `sentinel/api.py:130-133`. Memory is bounded (`200` incidents, `200` events)
    and refuses loudly instead of evicting live work. Plus: **212 tests**, one container, no
    framework, no build step, no CDN.

## Known limitations

Stated plainly, because a claim without a boundary is not evidence.

1. **Nothing is durable.** Workflow state and the idempotency ledger are in-process memory, capped
   at 200 incidents / 200 events, refusing with `503` rather than evicting live work. A restart
   clears both — so an event replayed after a redeploy becomes a new incident, and an incident id
   you were linked to stops resolving.
2. **Exactly one replica is a requirement**, not a preference. Two replicas would be two memories.
3. **Remediation is simulated.** There is no credential, no allowlist and no real action; the
   catalog has two entries.
4. **Synchronous and slow.** The producer's request is held for the whole inference (6.7–47.1 s
   measured, 90 s read budget, one attempt, no retries, no fallback). Survivable in a console;
   wrong for a paging system.
5. **Model quality is unmeasured.** The confidence figure is the model's own self-report, not
   accuracy scored against a labelled incident set. No accuracy claim is made anywhere.
6. **Security is one shared bearer token on one route.** No per-producer identity, no rotation, no
   expiry, no MFA. The public console is deliberately unauthenticated, and so is
   `POST /api/v1/incidents/analyze`.
7. **No live monitoring integration.** `scripts/send_demo_event.py` is a stand-in producer speaking
   a NovaOps-shaped contract; nothing consumes real alerts.
8. **`/openapi.json` omits the bearer requirement** on `/api/v1/events/ingest`. The contract is
   documented in [`../architecture/machine-event-ingestion.md`](../architecture/machine-event-ingestion.md)
   instead; fixing the schema needs a code change and a redeploy.
9. **`LEARN` is not built.** No memory, no policy refinement, no evaluation set. It is shown on the
   loop strip as *not implemented*.

## Final links

- Live demo: <https://sentinel.novatechsystem.co.uk>
- Source: <https://github.com/novatechsystemsgroup/novabrain-sentinel>
- Demo video: <https://youtu.be/bQLiWO1G5Mw> (2:29, YouTube, unlisted — plays without signing in)
- Health: <https://sentinel.novatechsystem.co.uk/health>
- [README](../../README.md) · [evidence matrix](evidence-matrix.md) ·
  [repeatable walkthrough](demo-scenario.md) · [project status](status.md)

Secrets are deliberately absent from this page: `NVIDIA_API_KEY` and `SENTINEL_INGEST_TOKEN` are
never published, printed or shared, and the analysis above references code paths rather than
configuration values.
