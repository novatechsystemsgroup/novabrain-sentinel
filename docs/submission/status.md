# Project Status — NovaBrain Sentinel

Last updated **2026-09-29**, during TASK-018 (final video URL and submission readiness). The
redeploy it had been waiting on has since landed, so the deployment rows below are stated as
measured rather than pending. This file is the roadmap in
one page: what is finished and evidenced, what is deliberately not built, and what is left before
the entry can be submitted. Deep detail lives in the documents linked from each line.

## Where the product stands

Sentinel is a **feature-complete hackathon entry** running as one container at
`https://sentinel.novatechsystem.co.uk`, with its source public at
`https://github.com/novatechsystemsgroup/novabrain-sentinel` (MIT). It receives an operational
event, assesses it with a real NVIDIA Nemotron call through a forced tool call, gates
`high`/`critical` incidents behind human approval in code, runs a **simulated** remediation after
that approval, verifies the simulated outcome, and appends every step to an audit trail — including
the attempts it refused. 212 tests, no build step, three environment variables.

It is not a production SRE platform and does not claim to be one.

## Milestones

| # | Milestone | State | Evidence |
|---|---|---|---|
| — | Bootstrap: FastAPI service, `/health`, landing page, Dockerfile, non-root image | **DONE** | `sentinel/api.py`, `Dockerfile` (`USER 10001`) |
| — | Development spike against the NVIDIA endpoint | **DONE, superseded** | TASK-002/003; replaced by the shipped analysis path |
| TASK-011 | Real NVIDIA incident analysis behind `POST /api/v1/incidents/analyze` | **DONE** | `sentinel/nvidia.py`, `analysis.py`; live runs since 2026-09 |
| TASK-012 | Approval workflow: state machine, deterministic policy floor, simulated action catalog, verification | **DONE** | `sentinel/workflow.py`, `simulation.py`; `docs/architecture/approval-workflow.md` |
| TASK-013 / 013A | Operational demo console: six panels, self-labelling loop strip, disclosure badge, CSP on `GET /` | **DONE** | `static/index.html`, `app.js`, `styles.css`; `docs/architecture/operational-console.md` |
| TASK-014 | Machine event ingestion: `POST /api/v1/events/ingest`, bearer guard before body parsing, in-process idempotency ledger, `event_ingested` audit event, `/?incident=<id>` console bridge, demo emitter script | **DONE** | `sentinel/ingestion.py`, `scripts/send_demo_event.py`; `docs/architecture/machine-event-ingestion.md`, ADR-0003 |
| TASK-015 | Submission readiness: requirements verification, evidence matrix, honest architecture, canonical demo scenario, video script + shot list, claims audit, secret scan, submission copy, checklist, this status file | **DONE** (code frozen; nothing added) | the pack under `docs/submission/` |
| — | Coolify deployment to the public URL | **DONE** | `docs/deployment/coolify.md`; live `/health` + browser QA |
| — | Production serving this tree, corrected copy included | **DONE** | measured 2026-09-29 against `16d20e6`: the served `GET /`, `/static/app.js` and `/static/styles.css` each hash byte-for-byte the same as the committed files, the empty state reads "allow up to 90s" with 0 hits for the retired range, the London eyebrow and `Event-driven operational agent` render with 0 hits for either retired string, and `POST /api/v1/events/ingest` answers `401` tokenless / `405` on `GET`. Nothing in the repository records what triggered the deploy (no webhook), so the served bytes are the evidence. |
| TASK-014 | Machine ingestion proven **on the public URL**: `201` → `/?incident=<id>` → replay `200 duplicate:true` | **DONE** | run made 2026-09-29 with the deployed `SENTINEL_INGEST_TOKEN` (never read by this pack): `novaops-public-demo-001` → `inc_a670b4d08a1848e997c4ed006e2842da`, `awaiting_approval`, replay `duplicate: True` on the same incident id; audit `Operational event ingested` → `Incident analyzed` → `Human approval requested`. Transcript and the limits of what this pass could re-verify in `checklist.md` §3 |
| TASK-015A | Final pre-video corrections: the empty-state wait copy now quotes the 90 s read budget instead of a measured 15–50 s band | **DONE, and live** | `static/index.html:124`; pinned by `tests/test_console.py::test_inference_wait_copy_promises_the_backend_read_budget`. No timeout changed. |
| — | Coolify redeploy so production serves the corrected copy | **DONE** | closed in TASK-017 by measurement, not by a deploy log: the two earlier rows said a redeploy was outstanding, and it has since landed. `checklist.md` §2 and §11 carry the hashes. |
| TASK-016 | Recording preparation: step-by-step runbook, narration cheat sheet, post-recording review checklist | **DONE** | `recording-runbook.md`, `narration-cheatsheet.md`, `video-review-checklist.md` |
| TASK-017 | Judge-facing entry point: 90-second browser walkthrough, real/simulated table, machine path without a shared secret, limitations, README link, repository description | **DONE** | `JUDGE-QUICKSTART.md`, `README.md` (one line above the fold), GitHub description read back |
| TASK-018 | Record, review and publish the demo video | **DONE** (the entry is not) | <https://youtu.be/bQLiWO1G5Mw> — "NovaBrain Sentinel — NVIDIA Claw Agent Challenge: London Demo", 2:29, YouTube, unlisted. `oEmbed` returns that title with author `NovaTech Systems Group` and the watch page serves `200` with this video id and 0 hits for the sign-in interstitial; the page's own duration fields straddle 2:28 and 2:29, so 2:29 is the uploader's figure and `video-review-checklist.md` carries the measurement. The end-to-end watch is the operator's attestation, not a repository measurement. `checklist.md` §9 holds the detail. |
| — | Fill and submit the Airtable entry form | **NEXT — deadline 2026-10-02 23:59 PST** | `requirements.md` #1, #5 |
| — | Final pre-submit smoke test on the public URL | **NEXT** | `checklist.md` §11 |

## Deliberately not implemented

Recorded so the absence reads as a decision rather than an oversight. None of it is claimed
anywhere in the submission pack, and the console labels `LEARN` as *not implemented yet* instead of
hiding the stage.

| Not built | Why it stayed out | What would be needed |
|---|---|---|
| Durable state (PostgreSQL, Redis, any store) | State is per-process memory bounded at 200 incidents and 200 events, refusing with `503` rather than evicting live work. Adding a database mid-submission would change the claims, not the product (`workflow.py:25,240`, `ingestion.py:18,140`). | A schema, migrations, and an honest rewrite of "what survives a restart" |
| Queues / background workers / async consumption | Ingestion is synchronous: the producer waits for the inference and gets the incident id in the response. A queue would make the `201` we demo not mean what it appears to mean. | A broker, a worker, and a job-status endpoint |
| Agent frameworks (LangGraph, AutoGen) | The loop is a state machine in `workflow.py`. A framework would add a dependency a judge has to install to understand. | Nothing; this is a preference, stated as one |
| Real remediation (orchestrator API calls) | `simulation.py` declares `simulated: True` and `executes: False` (`:27,:29`) and the catalog is closed (`:32-51`). Executing against infrastructure is out of scope for a hackathon entry. | Credentials, an allowlist, an audit of blast radius, and a very different demo |
| An auth system for the console | The console is public by design; only ingestion carries a secret. Roles, MFA and token rotation are a different product. | Identity provider integration |
| `LEARN` / memory | There is no feedback loop back into assessment. The stage exists in the loop diagram so the entry says which part of the agent loop is missing. | An evaluation set first — otherwise "learns" is decoration |
| Extra models, more providers, a local fallback | One NVIDIA endpoint, one model, one forced tool call. Multi-provider routing is not a submission claim, it is a submission distraction. | Nothing planned |
| Dashboards, monitoring stack, alerting | Sentinel *receives* events; it does not observe the world. The producers we speak to (`source=novaops`) are the observers. | A metrics pipeline we do not own |

## Open items that are not code

1. **Eligibility** — UK residency, 18+, individual entry, not a sponsor employee. A human fact
   (`requirements.md` #3, #4).
2. **Registration-gated rules** — real video cap, form fields, screenshot requirement, mandated
   model/NIM, originality clause. `UNKNOWN` until the form is opened; nothing was inferred from
   "how hackathons usually work".
3. **`/openapi.json` omits the bearer requirement** on `/api/v1/events/ingest` (0 occurrences of
   `Bearer` in the schema). Fixing it means editing `api.py`, which needs a redeploy to verify, so
   TASK-015 §0 records it as a known limitation instead. The contract itself is documented in
   `docs/architecture/machine-event-ingestion.md`.
4. **The standing secret guard does not cover this pack.**
   `tests/test_ingest.py::test_no_credential_shaped_text_in_shipped_files` sweeps `DOC_PATHS`
   (`:730-737`) plus `Dockerfile`, `static/app.js` and `static/index.html` — the parametrisation at
   `:787`, which is a named subset rather than the tree, and leaves out `static/styles.css` as well as
   `docs/submission/*.md`. Nothing fails the build if a value is pasted into a submission document later. The
   TASK-015 scan is a one-off sweep of the whole tracked tree instead; see
   [`security-check.md`](security-check.md) §In-repo guard. Adding this directory means
   editing a test, which §16 puts behind a stop-and-ask, so it is left as the first small piece of
   post-submission work rather than done here.

Closed since: the **repository description** that used to sit on this list is no longer open. TASK-017
set it through the GitHub API to "Event-driven operational agent — NVIDIA Claw Agent Challenge:
London" and read the value back; visibility and settings were not touched. It is a site-level field
rather than a file, so nothing in this tree can keep it that way — re-check it on the day the form is
filled. The video's last frame has already been recorded, so the window for catching it on camera has
passed; TASK-018 re-read the value on 2026-09-29 and it is still exactly that string, with visibility
still `public`.

## If work resumes after submission

The next honest step is not a feature. It is measuring whether the assessments are *right*: a
labelled incident set, scored against the model's severity, reported as accuracy rather than as the
model's own confidence number. Everything else on the not-built list is bigger, and none of it is
currently claimed.
