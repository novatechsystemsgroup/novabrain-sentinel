# Screenshot Plan — 6 crops

TASK-015 §13. **Committing no image binaries in this pass.** Whether the form asks for screenshots
is `UNKNOWN` — it is not on the public page (see [`requirements.md`](requirements.md), requirement
14) — and the brief is explicit: *"Do not commit arbitrary local screenshots yet unless the
competition actually needs them in the repo."* So this file is the specification; the files
themselves get captured once, in the same session as the video, from the same canonical run, and
attached only if the form has a field for them.

## Why screenshots come out of the video session

One producer run (`python scripts/send_demo_event.py`) drives all fifteen demo-scenario steps. The
six crops below are frames of that single run, so they cost **one** production incident rather than
six, which is what §10 asks for ("use the minimum runs required"). Shooting them separately would
mean re-running live inference six times to produce pictures of the same incident.

Capture settings for every browser crop: 1440 × 900 viewport, zoom 100 %, browser chrome excluded
from the export, DevTools closed except where a crop asks for it, no other tabs open, notifications
muted. Terminal crops: the window's own monospace at whatever size is legible at 100 % on a laptop
— if it is not readable there, the crop is too wide.

## The six crops

### 1 — `01-console-cold-open.png`  ·  from S01, S02

Full console at `https://sentinel.novatechsystem.co.uk`, nothing filled in, nothing running.

**Must be visible:** the address bar URL is *not* in the crop (browser chrome is excluded), so the
URL is carried by the page's own text instead — the eyebrow `NVIDIA Claw Agent Challenge: London`
(`static/index.html:13`) and the empty-state line that says a real model call takes tens of seconds
(`index.html:124`). The loop strip with its per-stage status chips (`index.html:27-44`) and the
footer badge `Real NVIDIA inference · Safe simulated remediation` (`index.html:179`) must both be
inside the frame.

**Proves:** the thing is live, public, unauthenticated, and labels its own stages before a judge
asks.

### 2 — `02-machine-intake.png`  ·  from S04, S07

Terminal, two stacked blocks in one image: the command line, then the response it printed.

**Must be visible:** `python scripts/send_demo_event.py --url https://sentinel.novatechsystem.co.uk`
with **no token on the command line and no `export …=<value>` in the visible scrollback**; then
`HTTP 201` and the five fields — `event_id: novaops-demo-0001`, `incident_id: inc_…`,
`workflow_state: awaiting_approval`, `duplicate: False`,
`console_path: /?incident=inc_…`.

**Proves:** a machine, not a person, opened this incident; the producer's own `severity_hint:
warning` produced a state that is already gated.

### 3 — `03-assessment-and-model.png`  ·  from S09

Panel 2 (Understand · Assessment) punch-in, `#panel-assessment`.

**Must be visible:** `severity: high`, the confidence value as the model returned it,
`requires_approval: true`, the one-sentence rationale, and the model line
`nvidia/nemotron-3.5-lightning-30b-a3b`. The producer's `warning` hint should be in the same frame
if the layout allows (panel 1 sits above it), because the hint→verdict gap is the claim.

**Proves:** real NVIDIA inference produced a structured verdict, and it overrode the hint.

**Do not:** retake this crop to land a specific confidence number. Measured range is 0.86–0.87;
whatever the run returns is the honest image.

### 4 — `04-gate-and-refusal.png`  ·  from S10, S11

Panel 3 (Decide · Approval gate) plus the blocked banner, with DevTools Network showing the
response.

**Must be visible:** the ⚠ HUMAN APPROVAL REQUIRED state; *Execute simulated action* disabled while
*Attempt Execution* is enabled (`static/app.js:472-476`); the `SIMULATED ACTION` badge
(`index.html:105`) in the same frame as the controls; the banner "Execution blocked by Sentinel
policy — Approval is required before this action can run."; and the network row `409` with
`"reason": "approval_required"` in the body preview.

**Proves:** the gate is enforced server-side before any action, and the refusal is a policy answer,
not a crash. This is the single most valuable still in the set.

### 5 — `05-verified-outcome.png`  ·  from S13, S14

Panel 5 (Verify · Outcome), with the `SIMULATED ACTION` label still on screen.

**Must be visible:** `VERIFIED` and `Simulation: YES · simulated` (`app.js:431,434`); the before→after
metrics exactly as the API returned them — `API replicas: 2 → 4`, `p95 latency (ms): 2400 → 610`,
`Error rate (%): 8.2 → 0.4`, `Service restarts: 0 → 0`; and the approval row naming the operator
(approved, `approval_granted`).

**Proves:** the action was simulated and says so in the same breath as its result; the verifier
compared the outcome against a recovery condition.

### 6 — `06-audit-trail-raw.png`  ·  from S14, S14b, S15

Two stacked blocks: the eight-row console trail, then the raw JSON from
`curl -s …/api/v1/incidents/<incident_id>`.

**Must be visible:** the console order — *Operational event ingested → Incident analyzed → Human
approval requested → Execution blocked by policy → Operator approved → Simulated action requested →
Simulated action finished → Outcome verified* — and, in the JSON block, the raw tokens
`event_ingested`, `execution_blocked`, `approval_granted`, `verification_recorded` with their actors
and timestamps. If room allows, add the replay block from S15: `HTTP 200`, `duplicate: True`, the
**same** `incident_id`, ~20 ms.

**Proves:** the machine path, the refusal and the approval are all recorded in append order, and a
retry costs nothing. The raw tokens only exist here — `renderAudit` maps every event through
`AUDIT_LABELS` (`static/app.js:457`), so no console-only screenshot can show them. That is why this
crop pairs the page with its own API response rather than pretending the UI is the source of truth.

## Coverage

| Required visible evidence (from §6) | Screenshot |
|---|---|
| Public demo URL | 1 (as page text; URL itself only in the video's address-bar shot) |
| NVIDIA model name | 3 |
| `event_ingested` | 6 |
| `approval_required` | 4 |
| `execution_blocked` | 4 (label), 6 (raw token) |
| Operator approval | 5 |
| `SIMULATED ACTION` label | 4, 5 |
| `VERIFIED` result | 5 |
| Full audit trail | 6 |
| `duplicate: true` replay | 6 (optional third block) |
| GitHub repository | video S16 only — a screenshot of the repo adds nothing the form will not already receive as a URL |

## If the form does ask for images

- Capture all six during the video session, from the one canonical run; do not stage them
  separately.
- PNG, 1440 × 900 window crops, no annotations, no arrows, no added text overlays — anything that
  is not what the product rendered is a claim we cannot defend.
- Commit them under `docs/submission/images/` in a **separate commit** (`docs: add submission
  screenshots`), so the submission-docs commit stays text-only and reviewable.
- Before committing, run the secret scan over them by eye: crop 2 is the one that can leak, because
  it is a terminal. Check the visible scrollback for an `export` line.
