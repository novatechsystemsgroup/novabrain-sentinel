# Submission Checklist

TASK-015 §14. Four buckets, and the split is the point: **DONE** means evidenced in this repository
right now, **MANUAL ACTION REQUIRED** means a human has to act outside the code, **BLOCKED** means
something we cannot close from here, **UNKNOWN** means the organiser has not published the rule so
we refuse to guess it.

Nothing in the Video or Submission-form sections is checked, because neither has happened. A
checkbox on those lines would be a claim with no evidence behind it.

State as of 2026-09-29, written against the code tree at `34e4053`. The submission pack — 12 new
files under `docs/submission/` plus the README and `docs/evaluation/README.md` updates — commits on
top of it and changes no code, so every `file:line` reference below holds for both. A file cannot
record its own push, so the push is a step in §2 verified by command, not a SHA typed into prose.

## 1. Competition requirements

- [x] Requirements read from the organiser's page, not assumed — `luma.com/claw-agent-challenge-london`,
  retrieved 2026-09-28 22:38 UTC; 17 lines recorded, each `PASS` / `PARTIAL` / `UNKNOWN` with a
  source. → [`requirements.md`](requirements.md)
- [x] Entry deadline recorded as binding: **2026-10-02 23:59 PST** (= 2026-10-03 06:59 UTC). The
  page also shows "14 Oct 2026 13:00 BST" for the London event; the earlier date is treated as the
  deadline and the discrepancy is documented rather than silently resolved.
- [x] Judging criteria mapped (technical execution / innovation / real-world value) without
  self-scoring, because no weights are published. → [`evidence-matrix.md`](evidence-matrix.md)
- [x] "A registration equates to a project submission" understood: one Airtable form, filled last.
- [ ] **MANUAL ACTION REQUIRED** — Eligibility is a human fact the repository cannot answer: UK
  legal residency, 18+, individual (not corporate) entry, not a sponsor's employee. Confirm before
  registering; if any of these fails, nothing else in this checklist matters.
- [ ] **UNKNOWN** — Real video length cap, prescribed form fields, screenshot/diagram requirement,
  mandated model or NIM, team-size and originality clauses. All sit behind the registration form.
  Read them after registering and re-cut only if our self-imposed 2:30–2:50 target was wrong.

## 2. Repository

- [x] Public repository with a licence: `https://github.com/novatechsystemsgroup/novabrain-sentinel`,
  visibility PUBLIC, MIT (`LICENSE`).
- [x] Tests green on the tree being submitted: **211 passed**, run as
  `.venv/bin/python -m pytest -q` (bare `pytest` fails collection — no `conftest.py`, so the repo
  root is not on `sys.path`). Re-run immediately before commit; the number in the completion report
  is the number from the final tree.
- [x] `docker build .` succeeds on the tree being submitted: `sha256:b38dbf9d…` (tag
  `novabrain-sentinel:qa-task015`), **246 MB**, `python:3.13-slim`, `USER 10001` verified inside the
  running container (`id -u` → `10001`), healthcheck `healthy`, `RestartCount: 0`. The build context
  copies only `requirements.txt`, `sentinel/` and `static/`, so this pack cannot change it.
- [x] Relative links resolve across `docs/` after this pack lands (link check re-run in §11 QA).
- [x] `git status` clean apart from this pack before committing; 36 tracked files at scan time.
- [ ] **MANUAL ACTION REQUIRED** — Push the commit carrying this pack, then verify
  `git rev-parse HEAD` equals `git rev-parse origin/main`. Until the two match, the public repository
  does not contain this pack and a judge following the URL sees only the previously pushed commit.
- [ ] **MANUAL ACTION REQUIRED** — The GitHub repository **description** still reads
  "Persistent Operational AI Agent". That is the exact claim the claims audit removed from the code
  (durability is per-process memory: `workflow.py:240`, `ingestion.py:140`). Edit it in repository
  settings to e.g. "Event-driven operational agent — NVIDIA Claw Agent Challenge". The audit could
  not fix it because it lives outside the repository. → `claims-audit.md`, *REMOVE* section.

## 3. Live demo URL

- [x] `https://sentinel.novatechsystem.co.uk` reachable: `GET /` 200 (0.177 s), `/health` 200
  `{"status":"ok","service":"novabrain-sentinel"}`, `/docs` 200, `/openapi.json` 200.
- [x] One container, one replica; strict CSP on `GET /` only, `/static/*` correctly without it.
- [x] Console QA at 1440 × 900 and 390 × 844: `scrollWidth − clientWidth = 0` at both, **0 JS
  errors**, the only console line being Chrome's own `409 (Conflict)` notice for the deliberate
  blocked attempt.
- [x] Bearer guard live: `POST /api/v1/events/ingest` without a token → `401` +
  `WWW-Authenticate: Bearer`; wrong token → `401`; `GET` on the route → `405`.
- [ ] **MANUAL ACTION REQUIRED** — **Redeploy, then re-verify two strings.** Production serves the
  image from the last deploy, not `main`, so the page renders the old eyebrow
  `NVIDIA Build Challenge` and the old subtitle **`Persistent Operational AI Agent`**
  (`static/index.html:13,15`). The corrected strings ("NVIDIA Claw Agent Challenge: London" /
  "Event-driven operational agent") exist only in the tree — `34e4053` and this pack — so they are
  invisible publicly until a redeploy. Everything else in the served page is byte-identical to the
  tree — I diffed it. The public landing page is the first
  thing a judge sees, and today it states the one claim this task set out to retire. **This needs
  explicit approval: TASK-015 §17 forbids an automatic deploy.** Shoot the video only after it.
- [ ] **MANUAL ACTION REQUIRED (needs the same approval as the line above)** — `static/index.html:124`
  still promises "about 15–50 seconds" against a measured **6.7–47.1 s**. The one-line edit
  (`15&ndash;50` → `7&ndash;47`) was **not** made: §16 says a code change is described, not slipped in,
  and no test pins the string, so nothing forces the timing. Full defect / impact / regression
  analysis is in [`claims-audit.md`](claims-audit.md), *Found, deliberately not edited*. If the
  redeploy is approved, decision requested: let this line ship inside that same deploy so the
  console and the README state one number, not two.
- [ ] **MANUAL ACTION REQUIRED** — Prove `201` + replay `duplicate:true` **on the public URL**. It
  needs `SENTINEL_INGEST_TOKEN` from the deployed runtime, which this QA pass deliberately did not
  read (names, not values). Evidence today: the full machine-first loop ran in a local container
  built from the same tree, and production proves only the rejection side. One run is enough; do
  not create a batch of production incidents.

## 4. NVIDIA integration

- [x] Live inference through the organiser's provided endpoint:
  `https://integrate.api.nvidia.com/v1` (`sentinel/nvidia.py:18`) with
  `nvidia/nemotron-3.5-lightning-30b-a3b` supplied as `NVIDIA_MODEL` (`nvidia.py:97`, no default).
- [x] Structured output enforced by a pinned forced tool call `submit_incident_assessment`,
  `temperature 0.1`, `top_p 0.9`, `max_tokens 4096` (`nvidia.py:140-143`); the payload is validated
  by pydantic, and an out-of-enum severity is a provider error rather than a guess.
- [x] Only `tool_calls[0].function.arguments` is read; `content` and `reasoning_content` are never
  surfaced (`nvidia.py:4`, asserted in `tests/test_console.py:502`).
- [x] Measured latency band across six live runs **6.7–47.1 s**, read timeout `90 s`; confidence
  observed 0.86–0.87. Documented as measured, never as a promise.
- [x] No second provider, no local fallback model, no fake-response switch in the shipped path.

## 5. Demo flow

- [x] One canonical scenario documented, 15 steps + step 14b, proven end to end: producer event
  (`source=novaops`, `event_type=ram_high`, `severity_hint=warning`) → `201` →
  `/?incident=<id>` → `high` + `requires_approval` → gate → `409` → approve → simulated scale →
  `verified` → 8-row trail → replay `duplicate:true`. → [`demo-scenario.md`](demo-scenario.md)
- [x] Console path proven **on production** (7-event trail, `inc_0a0d3648688244a4ac37a1763272cbd7`,
  `high` / `0.87`).
- [x] Fallback incidents recorded, and the rule that a fallback changes the *input*, never the
  output.
- [x] Corrected against the code: the console renders UI labels, not raw event tokens
  (`static/app.js:457` maps through `AUDIT_LABELS`), so `event_ingested` and `execution_blocked`
  are now shot from `GET /api/v1/incidents/<id>` in a terminal. Without this fix the shoot would
  have chased two frames that cannot exist in a browser.

## 6. Evaluation and evidence

- [x] `docs/evaluation/README.md` carries the TASK-015 submission QA section with measured timings,
  the local machine-first run, the public production run, and an explicit *Not proven on
  production* list.
- [x] Evidence matrix: implementation → artefact → demo moment → honesty note for every criterion.
- [x] Claims audit: swept twice — 42 files mid-task, then the **final 48-file tree**; 7 statements
  rewritten, 1 removed outright ("Defense in depth"), 1 factually inverted claim fixed
  (`frame-ancestors 'none'`), 11 stale `README.md:NNN` citations re-anchored after the README grew.
  → [`claims-audit.md`](claims-audit.md)
- [x] Honest limits kept in the text rather than footnoted: "long-running" is `PARTIAL`,
  remediation is simulated, NovaOps is a **compatible producer contract** and not an integration.

## 7. Security

- [x] Full secret scan on the final tree. Scan set: **47 files** — everything `git ls-files` and
  `git ls-files --others --exclude-standard` report (48), minus `security-check.md` itself, which has
  to be allowed to name the patterns it searches for. The byte total is recorded in that report and
  deliberately **not** here: this file is inside the set whose size it would be quoting, so it could
  never converge against itself. Result: **0 secret values.** 102 lines merely *name* a variable or
  pattern; exactly **6** put something in the value position, and each is listed with its reason
  (empty placeholder, two `...` ellipses, an f-string header, a regex source, a Mermaid cell). PEM,
  `AKIA…`, `ghp_…`/`github_pat_…` all **0**, in the tree and in history.
- [x] History swept with the same patterns over **all of `git log --all -p`**: the 9 commits that
  predate this pack (416,484 bytes / 9,539 diff lines / 7,532 added content lines) → **0**. That is a
  labelled baseline rather than a permanent total, because pushing this pack adds a tenth commit —
  and it adds no *new* text to scan, since the lines it appends are the documents the tree sweep
  above already covers one by one. The published history therefore stays at 0 for the same reason.
- [x] High-entropy sweep on the same 47 files: **0 credential-shaped candidates** — every run of ≥32
  word characters is classified (`test_*` identifiers, Markdown separator rules, public `inc_`
  incident ids, two hyphenated prose phrases). The census with its counts lives in
  [`security-check.md`](security-check.md), which is the one file allowed to carry them.
- [x] Every match is enumerated by file and line instead of hidden behind "nothing found"; the
  re-run commands are printed with their observed output, and re-run here: guard selections
  `26 passed` / `4 passed`, hard-format sweep silent (exit 1), history count `0` at the labelled
  baseline above, six production paths `0` each.
- [ ] Follow-on, not a submission blocker: the standing guard (`tests/test_ingest.py:788`) scans
  `DOC_PATHS` + `Dockerfile` + the three `static/` assets, so **`docs/submission/*.md` is outside
  it** — that directory is covered by the sweep above instead. Widening `DOC_PATHS` is a test
  change, which TASK-015 §16 says to ask about rather than slip into a docs commit.
- [x] `.env` absent from the working tree and from history (`.gitignore:2-4`); `.env.example`
  carries empty values only.
- [x] Six live production responses scanned: 0 occurrences of the NVIDIA key prefix, a `Bearer `
  literal, an `API_KEY=`/`TOKEN=` assignment, the provider hostname, `reasoning_content`, and
  `innerHTML`.
- [x] The previously exposed NVIDIA key is **revoked and rotated**; neither the old nor the new
  value appears in the repository, its history, any doc, the console, `/openapi.json`, a recorded
  command line, or in `security-check.md` itself.
- [x] In-repo regression guard: `tests/test_ingest.py::test_no_credential_shaped_text_in_shipped_files`
  fails the suite if a credential-shaped literal is added to its parametrisation list — `DOC_PATHS`,
  the Dockerfile, `static/app.js` and `static/index.html`. That is a named subset, not the tree: see
  the follow-on item above for what sits outside it.
- [x] Residual risks documented rather than claimed away: the console and `/api/v1/incidents/analyze`
  are unauthenticated by design, one shared bearer token guards ingestion, and state is
  per-process. → [`security-check.md`](security-check.md)
- [ ] **UNKNOWN** — Whether the organisers require a security questionnaire. Not on the public page.

## 8. Documentation

- [x] `docs/submission/requirements.md`
- [x] `docs/submission/evidence-matrix.md`
- [x] `docs/submission/architecture.md` — one Mermaid diagram, REAL / SIMULATED / NOT IMPLEMENTED,
  one container one replica, in-memory state, unauthenticated console, bearer-protected ingestion
- [x] `docs/submission/demo-scenario.md`
- [x] `docs/submission/video-script.md`
- [x] `docs/submission/video-shot-list.md`
- [x] `docs/submission/claims-audit.md`
- [x] `docs/submission/security-check.md`
- [x] `docs/submission/submission-copy.md` — all nine blocks inside their word budgets (measured:
  120 / 149 / 220 / 122 / 180 / 127)
- [x] `docs/submission/screenshots.md` — 6 crops specified; **no image binaries committed**, because
  requirement 14 is `UNKNOWN` and §13 says not to commit them unless the form needs them
- [x] `docs/submission/checklist.md` (this file)
- [x] `docs/submission/status.md` — the roadmap/status record (§15), which did not exist before
- [x] `README.md` reads as a cold judge can follow: demo URL near the top, "event-driven operational
  agent", "receives operational events from a monitoring system", no "continuously monitors
  everything", no production-NovaOps claim
- [ ] **MANUAL ACTION REQUIRED** — Attach screenshots only if the form asks for them; capture during
  the video session so it costs one production run rather than six.

## 9. Video

- [x] Script written: 2:30–2:50 self-imposed target, 9 narration blocks, and it says **"Real NVIDIA
  inference. Safe simulated remediation."** out loud.
- [x] Shot list written: 17 shots in edit order, 11 required visible-evidence items mapped,
  legibility rule ("record wide, then punch in"), fallback per shot.
- [ ] **Record the video.** Not started. Nothing here is done until a file exists.
- [ ] **Watch it end to end** at 100 % zoom on a laptop-sized window, confirming the coverage table
  in `video-shot-list.md` line by line.
- [ ] **Upload / publish** at whatever host the form asks for (UNKNOWN until registered), then
  confirm the link plays for a signed-out visitor.
- [ ] Re-cut **only if** the published cap turns out to differ from our target.

## 10. Submission form

- [ ] Register at `https://airtable.com/appbWMw3ySORLZTgV/pagLOxwVLzgiOaunm/form` (registration
  *is* the submission — do not register early and assume the entry is in).
- [ ] Transcribe the blocks from `submission-copy.md` into whatever the form actually asks for;
  discard our field names if they differ from the published ones.
- [ ] Paste the demo URL `https://sentinel.novatechsystem.co.uk`, the repository URL, and the video
  link.
- [ ] Final pre-submit read: does any sentence promise more than `claims-audit.md` supports?
- [ ] **Submit**, then record the timestamp. Deadline **2026-10-02 23:59 PST**.

## 11. Final smoke test (after the redeploy)

- [ ] `GET /` still 200 and now rendering `Event-driven operational agent` with the London eyebrow.
- [ ] `/health` → `{"status":"ok","service":"novabrain-sentinel"}`.
- [ ] One cold console run: *Run Demo Incident* → `high` → gate → refuse → approve → execute →
  `VERIFIED`.
- [ ] One machine run against the public URL: `201`, open `/?incident=<id>`, replay → `200
  duplicate:true` with the same incident id.
- [ ] Secret sweep over the two responses (`/`, `/openapi.json`): 0 hits.
- [ ] `git rev-parse HEAD` equals `git rev-parse origin/main`, working tree clean.

## Blocked

- [x] Nothing in this task is blocked by the code. Two items are blocked on access I deliberately do
  not have: the deployed `SENTINEL_INGEST_TOKEN` value (line 3.6) and the registration-gated rules
  (line 1). Both are named as such rather than worked around — reading a production secret to tick a
  box would be exactly the kind of claim this pack is trying to retire.
