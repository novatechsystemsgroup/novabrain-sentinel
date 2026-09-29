# Canonical Demo Scenario

TASK-015 §4. One scenario, run in this order, already proven end to end on 2026-09-28 in a
rebuilt container (see [`docs/evaluation/README.md`](../evaluation/README.md), *Submission QA —
TASK-015*). It is the scenario the video shoots; do not invent a second one.

**Framing to say out loud before step 1:** *Real NVIDIA inference. Safe simulated remediation.*
That exact sentence is also on the console as a disclosure badge (`static/index.html:179`).

## The event

The canonical machine-first event is exactly what `scripts/send_demo_event.py:31-45` emits — do
not hand-edit it, because the payload and the docs must not diverge:

```json
{
  "event_id": "novaops-demo-0001",
  "source": "novaops",
  "event_type": "ram_high",
  "title": "API latency spike",
  "description": "p95 latency increased from 180ms to 2.4s",
  "severity_hint": "warning",
  "evidence": [
    "error rate increased to 8.2%",
    "CPU increased to 91%",
    "memory pressure reported by the host agent"
  ]
}
```

`severity_hint: warning` matters: it is the part of the demo where a producer's own understated
guess is overridden by the model, which is what "a hint only" means on the form
(`static/index.html:89`).

## Preconditions

- Backend reachable and healthy: `GET <url>/health` → `{"status":"ok","service":"novabrain-sentinel"}`.
- `SENTINEL_INGEST_TOKEN` exported in the *terminal* session only, never in a command line, never
  in a file that gets committed (`scripts/send_demo_event.py:10`).
- Browser at 1440 × 900, zoom 100 %, DevTools closed until the terminal frames.
- One container, one replica. Do not run this against two replicas.

## The 15 steps

Each step lists what the operator does, what must be visible, and what to do if it is not.

| # | Action | Must be visible | If it is not |
|---|---|---|---|
| 1 | In the terminal, `python scripts/send_demo_event.py --url <url>` | The command line itself, with no token in it | Reshoot; a token visible in shell history is a failed take |
| 2 | Wait for the response (6.7–47.1 s live) | Elapsed wall time, then `HTTP 201` | If `401`: token mismatch — re-export and retry. If `503 ingest_not_configured`: the deployed runtime has no token |
| 3 | Read the five printed fields | `event_id: novaops-demo-0001`, a new `incident_id: inc_…`, `workflow_state: awaiting_approval`, `duplicate: False`, `console_path: /?incident=inc_…` | If `workflow_state` is `analyzed`, the model rated this below `high` — see the honesty note below |
| 4 | Open `<demo-url><console_path>` in the browser | The incident loads by id; panel 1 shows the producer's event, not a typed question | If the panel is empty, the incident was evicted or the id is wrong — re-run step 1 |
| 5 | Panel 6, first audit line | `Operational event ingested` (the UI label) with actor `sentinel` | The raw token `event_ingested` is **not** in the DOM — `static/app.js:457` maps every event through `AUDIT_LABELS`, so the raw spelling only exists in the API JSON (step 14b) |
| 6 | Panel 2, the assessment | `severity: high`, `confidence` (measured 0.86–0.87), `requires_approval: true`, the model name, one-sentence rationale | Do not re-shoot for a specific confidence number — see below |
| 7 | Point at the model name line | `nvidia/nemotron-3.5-lightning-30b-a3b` on screen | If absent, the deployment is misconfigured — stop the demo |
| 8 | Note the severity hint vs the verdict | `warning` in, `high` out | This is the point of the take; if the model agrees with the hint, it is still honest, just less sharp |
| 9 | Panel 3, the gate | The ⚠ HUMAN APPROVAL REQUIRED state, and the loop strip showing ACT as mixed — "Approval: REAL / Action: SIMULATED" | If the gate reads "No approval required", severity was below high |
| 10 | Click *Attempt Execution* **before** approving | The banner "Execution blocked by Sentinel policy — Approval is required before this action can run.", from a `409` | A `200` here is a product defect, not a retake — stop and report it |
| 11 | Panel 6, the refusal | `Execution blocked by policy` (label for `execution_blocked`), actor `operator`, details line `action: … · reason: approval_required` | If missing, the audit leg is broken |
| 12 | Click *Approve*, then *Execute simulated action* | State `verified`; `Simulation: YES · simulated`; the `SIMULATED ACTION` badge still visible | If *Execute* stays disabled, the approval did not record |
| 13 | Panel 5, the outcome | Before → after exactly as returned: replicas `2 → 4`, p95 `2400 → 610`, error rate `8.2 → 0.4`, restarts `0 → 0` | Any other numbers mean the frontend invented them — that is a defect, not a retake |
| 14 | Panel 6, the whole trail | 8 rows in append order, as UI labels: `Operational event ingested → Incident analyzed → Human approval requested → Execution blocked by policy → Operator approved → Simulated action requested → Simulated action finished → Outcome verified` | Fewer than 8 means a step was skipped or the trail lost an append |
| 14b | In the terminal, `curl -s <url>/api/v1/incidents/<incident_id>` | The **raw** event tokens in the same order: `event_ingested`, `incident_analyzed`, `approval_requested`, `execution_blocked`, `approval_granted`, `execution_requested`, `execution_finished`, `verification_recorded` — plus `"simulated": true`. This is the only frame where the raw spellings exist on screen | If the JSON shows fewer names, step 14 is cosmetic — the API is the source of truth |
| 15 | In the terminal, re-run the identical command | `HTTP 200`, `duplicate: True`, **the same `incident_id`**, `workflow_state: verified`, answered in ~20 ms with no second inference | A second `201` means the ledger lost the claim (restarted or duplicated process) — say so on camera rather than hiding it |

## The honesty rules that govern this scenario

- **Do not depend on the model producing one exact sentence.** Rationales vary; the assertions
  that must hold are `severity: high`, `requires_approval: true`, and a model name present.
  Confidence is quoted as a measured range (0.86–0.87), never as a fixed figure.
- **Never edit a model output.** If a run is weak, re-run it or switch to the fallback incident.
  Cutting between takes is fine; fabricating a response is not.
- **A blocked execution is the payload, not a failure.** Step 10's `409` is the reason the demo
  exists. Chrome's console will log one red network line for it — expected, and stated in the
  shot list.
- **`restart_api_service` is the honest second option.** It is modelled as *insufficient* for a
  `critical` incident (`simulation.py:42-50`), so choosing it after a `critical` verdict produces
  `failed` rather than `verified`. Good if you want to show the verifier disagreeing; risky on
  camera, so the canonical take uses `scale_api_replicas`.

## Fallback incidents

Use these only if the canonical event repeatedly produces a boring assessment, and keep the
framing identical. Neither is falsified — both were observed:

1. **The console's prefilled demo incident** (`source=novaops`, `title="API latency spike"`,
   `severity_hint=unknown`, evidence `error rate increased to 8.2 %` and `CPU increased to 91 %`).
   Proven at 1440 px and 390 px, and it also returned `high` from an `unknown` hint — the
   strongest available evidence that the hint is not steering the model.
2. **A stronger payload on the same contract** — same `source`/`event_type`, with the description
   raised to a paging-grade symptom. Re-run from the script so the payload stays in the repo and
   is never typed live.

The fallback is a different *input*, never a different *output*.
