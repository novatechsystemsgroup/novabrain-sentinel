# Claims Audit

TASK-015 §8. Every promotional or security sentence in the shipped repository was read against the
code it describes and classified **SUPPORTED** (keep), **NEEDS QUALIFIER** (rewrite so the scope is
stated), or **REMOVE** (delete: the claim is not true at this commit). Nothing here is a style pass —
each row names the file:line that decides it.

## Scan scope

Tracked files (36) plus the `docs/submission/` files written for this task — the sweep ran twice,
once on 42 files mid-task and once on the **final tree of 48 files**, so the counts below are the
shipped ones. Every Markdown, `static/`, `sentinel/` and `scripts/` file is in scope. Pattern list
from the brief plus the marketing absolutes a cold judge would catch:
`autonomous`, `persistent`, `continuously`, `real-time`, `production`, `monitor*`, `verif*`,
`remediat*`, `NovaOps`, `NVIDIA`, `security`, `authenticat*`, `memory`, `self-heal`, `sanitize`,
`guarantee`, `open-source`, `state-of-the-art`, `all inputs`, `secure`, `zero-trust`,
`enterprise-grade`, `never fails`.

One caveat, or the counts read as false: this file quotes those words in its own pattern list and
verdict lines, so it matches its own sweep. The counts below are **hits outside this file**.

Results on the final tree, clean ones recorded rather than omitted: `real-time` **0**, `in real
time` **0**, `sanitiz*` **0**, `open-source` **0**, `state-of-the-art` **0**, `zero-trust` **0**,
`enterprise-grade` **0**, `never fails` **0**, `all … inputs` **0**, `continuously` **0** (its only
two other appearances are `checklist.md` §8 (the README line restating the rule) and
`requirements.md:20` quoting the organiser's brief). `guarantee` has **4** hits and all four are
negative or scoped — "nothing
guarantees that gap" (`approval-workflow.md:146`), "the guarantee is 'no duplicate inference within
a running process'" (`machine-event-ingestion.md:117`), "One field, one guarantee" (`0003:79`), "the
ordering guarantee in …" (`coolify.md:54`, describing a documented limit). `secure` has **1** hit and
it argues *against* a rejected alternative: "a callback surface to secure"
(`docs/decisions/0003-machine-event-ingestion.md:164`). `self-heal` has **1** hit
(`machine-event-ingestion.md:126`) and is mechanical, not agentic — an idempotency entry pointing at
an incident the store no longer holds is deleted and the event is reprocessed. `autonomous` has **4**
hits: three negations ("no such incident executes autonomously", `README.md:446`; "No high or
critical incident ever executes autonomously", `approval-workflow.md:103`; a rejected alternative,
`0002:121`) and one describing the failure mode Sentinel avoids (`submission-copy.md:25`).
`persistent` has **5** hits and every one quotes the retired subtitle `Persistent Operational AI
Agent` in order to record that it is being removed.

## Loop wording — the standard every other sentence defers to

| Stage | Status | Backing code |
|---|---|---|
| OBSERVE | **REAL** | `POST /api/v1/events/ingest` + `POST /api/v1/incidents/analyze` (`api.py`) |
| UNDERSTAND | **REAL** | NVIDIA Nemotron over the OpenAI-compatible endpoint (`nvidia.py:18`, `nvidia.py:97`) |
| DECIDE | **REAL** | deterministic policy, `APPROVAL_FLOOR = {"high","critical"}` (`analysis.py:12-18`) |
| REQUEST APPROVAL | **REAL** | workflow state machine + gate (`workflow.py`) |
| ACT | **SIMULATED** | closed two-entry catalog, `executes: Literal[False]` (`simulation.py:29`, `:32-51`) |
| VERIFY | **SIMULATED** | deterministic before/after snapshots (`simulation.py`) |
| AUDIT | **REAL** | append-ordered trail, in-memory, bounded at 200 (`workflow.py:25`) |
| LEARN | **NOT IMPLEMENTED** | no code path exists |

This table is the version reproduced in `architecture.md`, `evidence-matrix.md`, the README loop
section and the console footer. Any sentence that contradicts it is a defect.

## SUPPORTED — kept as written

| Claim | Where | Why it holds |
|---|---|---|
| Real NVIDIA inference, model named | `README.md:368-370`, `index.html:179`, `nvidia.py:18/97` | A live provider call is made with `NVIDIA_MODEL`; the slice has no fallback model and no default (`nvidia.py:97`) |
| Only validated tool arguments are parsed | `video-script.md` block 4, `nvidia.py:4` | Reader touches `tool_calls[0].function.arguments` and never `content`/`reasoning_content`; enforced by `tests/test_console.py::test_ui_does_not_fake_progress_or_read_hidden_reasoning` |
| Machine event ingestion with bearer guard | `README.md:290-294`, `ingestion.py:47-73` | `hmac.compare_digest`, guard runs before body parse, `401` + `www-authenticate: Bearer`, `503 ingest_not_configured` when unset |
| Real, deterministic policy; the model cannot remove the gate | `README.md:445-446` | `apply_approval_policy` (`analysis.py:12-18`) sets `requires_approval` from the severity floor after the model answers |
| Real approval state machine and refusal path | `workflow.py`, `execution_block_reason` (`workflow.py:70-83`) | Pre-approval execute returns `409 approval_required` and appends `execution_blocked` |
| Real audit trail | `workflow.py` | Append-ordered events with actor + timestamp; replayed verbatim by the console |
| Idempotency **within the running process** | `ingestion.py:77`, `machine-event-ingestion.md:117` | Scoped wording already present: replay returns `200 duplicate:true`, restart clears the ledger and this is stated |
| "receives operational events from a monitoring system" | `README.md:5` | Contract-shaped; no claim that a monitoring product is wired |
| "no such incident executes autonomously" | `README.md:445-446`, `approval-workflow.md:103` | True by construction: the only executor is the simulated catalog behind the gate |

## NEEDS QUALIFIER — rewritten in this pass

| Original wording | Problem | New wording | Where |
|---|---|---|---|
| "**Input validation** — All external inputs are validated and sanitized" | "sanitised" is false: no string is escaped or rewritten; the console's defence is `textContent`, and nothing rejects unknown fields (no `extra="forbid"` in `schemas.py`) | typed-pydantic statement with the actual constraints (`min_length` `schemas.py:44-45`, `:60-63`; 240-char note cap `:21`, `:170-178`; `Literal` allowlists `:8-25`) plus "Nothing is 'sanitised' — … rendered through `textContent`, never `innerHTML`" | `README.md:469-474` |
| "**Least privilege** — Minimal permissions for each component" | "minimal permissions" implies credentials that could be narrowed; there are none to narrow | "the runtime holds two secrets and no infrastructure credential of any kind: it has no orchestrator, database or shell to reach, because the action catalog is two in-process metric snapshots (`simulation.py:32-51`)… UID 10001 (`Dockerfile:24`)" | `README.md:454-457` |
| "**Defense in depth** — Multiple layers of security controls" | No layers exist; one bearer guard on one route. Pure security theatre | *removed outright* | README security list |
| "using the NVIDIA **open-source** model" | licence characterisation of `nemotron-3.5-lightning-30b-a3b` was never verified from the model card in this session | "using the NVIDIA model" | `README.md:368-370` |
| "the only outbound network call in **the codebase** is the NVIDIA inference request" | `scripts/send_demo_event.py` also makes an outbound call, so the word "codebase" over-scoped it | "the **service's** only outbound network call is the NVIDIA inference request in `nvidia.py` (`nvidia.py:166-167`)" | README security list |
| "no `frame-ancestors`" (describing the console CSP) | Factually inverted: `CONSOLE_CSP` ends with `frame-ancestors 'none'` (`api.py:40`) | "`frame-ancestors 'none'`" | `README.md:458-461` |
| "**Sentinel** — Competition product — **integrates reusable components from NovaBrain and NovaOps**" | No component is extracted from either repo, and NovaOps publishes no licence grant; "integrates" described a repository relationship that does not exist | table now marks NovaBrain "this slice does **not** draw on yet", NovaOps "a **design reference, not a wired integration**", Sentinel "written in this repository, self-contained", followed by "No component has been extracted from either repository… nothing has exercised that permission" | README *Repository Relationship* |

## REMOVE — checked, none needed beyond the deletion above

Searched for the seven claims the brief forbids and confirmed none is asserted anywhere in the
shipped docs: durable audit persistence, real infrastructure remediation, `LEARN` implemented,
full-application authentication, production-grade high-throughput ingestion, actual NovaOps
integration, autonomous `high`/`critical` remediation. Two near-misses were already scoped by
earlier wording — `machine-event-ingestion.md:204` states the endpoint is "**not** a
production-grade high-throughput webhook receiver", and `README.md:335-338` repeats it — so they are
recorded as SUPPORTED-by-negation rather than rewritten.

The one place the forbidden wording still lives is **outside** the repository: the GitHub
repository *description* reads "Persistent Operational AI Agent", which asserts both persistence
(§ known-limitation) and a self-running agent. It is a settings field, not a file, so no commit
can fix it — see `checklist.md`, MANUAL ACTION REQUIRED.

## Wording standard adopted

Per §7: "event-driven operational agent", "receives operational events from monitoring systems".
Never: "continuously monitors everything", "monitors your entire infrastructure", "autonomous
remediation", "NovaOps is integrated in production". The console's own disclosure badge
(`index.html:179`) and footer Real/Simulated lists (`index.html:183-198`) are the in-product
version of this standard, which is why the audit treats them as evidence rather than copy.

## Checked and left unchanged

- `README.md` and `docs/architecture/machine-event-ingestion.md` both say the bearer guard covers
  ingestion; both already state the console and `analyze` are unauthenticated. Verified consistent,
  no change needed.
- The production timings quoted in `docs/evaluation/README.md` *Submission QA* re-checked against the
  runs in §10 and left as measured.

## Found and fixed: the stale wait estimate in shipped UI copy

The audit's rule is that any sentence contradicting the measured loop is a defect. This one did,
and it was the only remaining instance.

| | |
|---|---|
| **Defect** | `static/index.html:124` promised "a real NVIDIA model call takes about 15–50 seconds." Six live runs measured **6.7–47.1 s** (`docs/evaluation/README.md`). Both bounds were wrong: the lower bound was never reached (a run came in at 6.7 s), and the upper bound was never reached either. |
| **Consistency** | Every other document carried the corrected band — `README.md:387`, `README.md:415`, `README.md:512`, `docs/deployment/coolify.md:107` and `:215`, `docs/architecture/incident-analysis.md:100`, `docs/submission/submission-copy.md:140`, and the *Inference latency is survivable* row of `evidence-matrix.md`. The UI string was the last hold-out, so a judge who compared the console's own wording with the README found a disagreement inside the submission. After the fix the two disagree in the safe direction: prose still quotes the measured 6.7–47.1 s, the screen quotes only the enforced budget, and neither promises a bound the next run can break. |
| **Submission impact** | Moderate and self-inflicted: the whole entry is built on "we say what we measured." A number on screen that we did not measure is exactly the kind of claim §8 exists to catch, and it is visible in shot S01. |
| **Fix applied** | TASK-015A rewrote the one line to **"A real NVIDIA model call can take tens of seconds — allow up to 90s."** This differs from the fix this audit originally proposed (`15&ndash;50` → `7&ndash;47`), and deliberately so: re-pinning a measured band only resets the clock on the same defect, because the next slow run makes the sentence false again. A budget the code actually enforces cannot drift out of date, and `static/app.js` already phrased the wait that way (`:281` "allow up to 90s", `:98` "Inference is given 90 seconds"), so the console's two surfaces now say the same thing. `int(READ_TIMEOUT)` is the source of the number (`sentinel/nvidia.py:25`); **no timeout was changed.** |
| **Now pinned** | `tests/test_console.py::test_inference_wait_copy_promises_the_backend_read_budget` reads the placeholder out of `static/index.html`, asserts it quotes `int(READ_TIMEOUT)` and rejects any `N–M seconds` range. It failed against the old copy and passes against the new one, which is what the original "no test pins this string" gap needed closing. |
| **Shipping status** | Text only, one paragraph node, no selector, id or length dependency — the edit carries no regression risk. The risk was always in shipping it: `static/` is baked into the image, so production still serves the old sentence until a Coolify redeploy runs. **That redeploy is required and was not performed** (TASK-015A §3 forbids an automatic deploy); tracked in [`checklist.md`](checklist.md) *Redeploy required*. |

The earlier revision of this section recorded it as *deliberately not edited*, because TASK-015 §16
gated a code change on a decision this pass could not make for itself. That decision was made, the
edit was a one-line copy change plus its test, and the defect is closed in code while still open in
production — which is why the deploy, not the diff, is what the checklist now carries.

