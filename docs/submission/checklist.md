# Submission Checklist

TASK-015 §14. Four buckets, and the split is the point: **DONE** means evidenced in this repository
right now, **MANUAL ACTION REQUIRED** means a human has to act outside the code, **BLOCKED** means
something we cannot close from here, **UNKNOWN** means the organiser has not published the rule so
we refuse to guess it.

The Video section is checked for the three things TASK-018 was given leave to mark: recording
complete, upload complete, a public share link that resolves. The Submission-form section is **not**
checked, because the form has not been filled — a checkbox there would be a claim with no evidence
behind it.

State as of 2026-09-29, written against the code tree at `34e4053`. The submission pack — 12 new
files under `docs/submission/` plus the README and `docs/evaluation/README.md` updates — commits on
top of it and changes no code, so every `file:line` reference below holds for both. A file cannot
record its own push, so the push is a step in §2 verified by command, not a SHA typed into prose.

**Production serves this tree's copy.** TASK-015A changed one line of `static/index.html` (the
empty-state wait copy, §3) and deployed nothing — the brief forbids it. Re-measured 2026-09-29 at
`16d20e6`: the served `GET /`, `/static/app.js` and `/static/styles.css` hash byte-for-byte the same
as the tree (`256ef8b0…`, `5882a5f2…`, `79254759…`), so the corrected wording is live, and the video
was recorded against the public URL with **no redeploy outstanding**. How the deploy happened is
not recorded anywhere in the repository, because no webhook is configured
(`docs/deployment/coolify.md` documents manual deploys); the served bytes are the evidence.

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
  Read them after registering and re-cut only if our self-imposed 2:30–2:50 target was wrong. The
  exported take is **2:29**, 1 s under the floor of that band, so a stated minimum below 2:29 costs
  nothing and a stated minimum above it costs a re-cut.

## 2. Repository

- [x] Public repository with a licence: `https://github.com/novatechsystemsgroup/novabrain-sentinel`,
  visibility PUBLIC, MIT (`LICENSE`).
- [x] Tests green on the tree being submitted: **212 passed**, run as
  `.venv/bin/python -m pytest -q` (bare `pytest` fails collection — no `conftest.py`, so the repo
  root is not on `sys.path`). Re-run immediately before commit; the number in the completion report
  is the number from the final tree. TASK-015A added one test, the copy guard in
  `tests/test_console.py::test_inference_wait_copy_promises_the_backend_read_budget`.
- [x] `docker build .` succeeds on the tree being submitted: `sha256:b38dbf9d…` (tag
  `novabrain-sentinel:qa-task015`), **246 MB**, `python:3.13-slim`, `USER 10001` verified inside the
  running container (`id -u` → `10001`), healthcheck `healthy`, `RestartCount: 0`. **That digest is
  superseded for the submitted tree:** the build context copies `requirements.txt`, `sentinel/` and
  `static/`, and TASK-015A edited `static/index.html:124`, so the image baked before that edit no
  longer matches the tree. Re-built after the copy fix (digest in `evidence-matrix.md`).
- [x] Relative links resolve: over the 24 Markdown files `git ls-files` reports, 61 relative links
  (60 before TASK-015A added the `approval-workflow.md` citation to `docs/evaluation/README.md`),
  **0 broken**, re-run on the final tree. The set comes from `git ls-files`, not `find`: an earlier
  figure of 25 files here came from a `find`-based sweep, which also picked up
  `.pytest_cache/README.md` — an ignored, generated file that is not in the repository and so is
  not a document anyone submits.
- [x] `git status` clean; the tree is 48 tracked files, 0 untracked (36 before this pack, which added
  the 12 documents in `docs/submission/`). Byte total lives in `security-check.md`.
- [x] `git push origin main` done for the commit carrying this pack (`ec4cd45`), and
  `git rev-parse origin/main` verified equal to it — the public repository contains this pack, not
  just the pre-QA tree. Docs corrections committed afterwards are pushed the same way; the final SHA
  belongs to the completion report, since no file can quote the commit that creates it.
- [x] GitHub repository **description** corrected in TASK-017 to "Event-driven operational agent —
  NVIDIA Claw Agent Challenge: London", set through the GitHub API and read back with
  `gh repo view novatechsystemsgroup/novabrain-sentinel -q .description`. Visibility stayed public and
  no other setting was touched. It contradicted the claim the audit removed from the code (durability
  is per-process memory: `workflow.py:240`, `ingestion.py:140`), which is why it had to change before
  the video's last frame → `claims-audit.md`, *REMOVE* section. That frame has now been recorded, and
  because the value lives outside the repository no commit can keep it correct: re-check it on the day
  the form is filled.

## 3. Live demo URL

- [x] `https://sentinel.novatechsystem.co.uk` reachable: `GET /` 200 (0.177 s), `/health` 200
  `{"status":"ok","service":"novabrain-sentinel"}`, `/docs` 200, `/openapi.json` 200.
- [x] One container, one replica; strict CSP on `GET /` only, `/static/*` correctly without it.
- [x] Console QA at 1440 × 900 and 390 × 844: `scrollWidth − clientWidth = 0` at both, **0 JS
  errors**, the only console line being Chrome's own `409 (Conflict)` notice for the deliberate
  blocked attempt.
- [x] Bearer guard live: `POST /api/v1/events/ingest` without a token → `401` +
  `WWW-Authenticate: Bearer`; wrong token → `401`; `GET` on the route → `405`. The answer is `401`,
  not `503 ingest_not_configured`, so the deployed runtime **does** have `SENTINEL_INGEST_TOKEN`
  set — its value is deliberately not read here (names, not values).
- [x] **Production serves the deployed code.** Re-checked 2026-09-29 against `4cc545a`: `GET /` renders
  the corrected eyebrow `NVIDIA Claw Agent Challenge: London` and subtitle `Event-driven operational
  agent`, with **0** hits for either retired string (`NVIDIA Build Challenge`, `Persistent
  Operational AI Agent`). All three static files were byte-identical to the tree at that commit —
  `index.html`, `app.js` and `styles.css` each hash the same served as committed — and
  `POST /api/v1/events/ingest` answers `401`, so the TASK-014 route is live too. `/openapi.json`
  lists 8 paths, matching `sentinel/api.py`. Nothing in the repository records what triggered that
  deploy (`docs/deployment/coolify.md` documents no webhook), so the evidence is the served page,
  not a deploy log. Earlier drafts of this checklist said a redeploy was still pending; that was
  overtaken by events, and the fix here was to the document, not the service. **No deploy was
  performed for this task** — nothing in it needed one.
  **The equivalence still holds after the copy fix below.** That edit changed `static/index.html` in
  the tree, which would have made the served page stale again; re-measured 2026-09-29 at `16d20e6`,
  the served page hashes identically to the tree once more, so the corrected wording is live and no
  redeploy is outstanding.
- [x] **`static/index.html:124` wait copy corrected.** It used to promise "a real NVIDIA model call
  takes about 15–50 seconds", a measured band from six runs (actual **6.7–47.1 s**) whose lower bound
  had already been undercut, so a slower run made the console's own empty state a false promise to the
  judge reading it. TASK-015A replaced the range with the durable form — "A real NVIDIA model call can
  take tens of seconds — allow up to 90s" — which matches what the client actually enforces
  (`READ_TIMEOUT = 90.0`, `sentinel/nvidia.py:25`) and what `static/app.js` already said
  (`:281`, `:98`). **No backend timeout was changed.** The copy is now pinned by
  `tests/test_console.py::test_inference_wait_copy_promises_the_backend_read_budget`, which asserts
  the placeholder quotes `int(READ_TIMEOUT)` and rejects any `N–M seconds` range, so the number can no
  longer drift from the code it describes. Full defect history in
  [`claims-audit.md`](claims-audit.md), *Found and fixed*. Verified rendered, not just written: the
  `qa-task015a` image built from this tree serves the sentence over `GET /`, and in a browser at
  1440 × 900 it is one line of the `.placeholder` style it already used and at 390 × 844 it wraps to
  three with `scrollWidth − clientWidth = 0` and **0** console messages. Production was re-fetched
  later the same day and now serves the corrected sentence: on the served `GET /`,
  `grep -c 'takes about'` → `0` and `grep -c 'allow up to 90s'` → `1`. An earlier pass in TASK-015A
  recorded `1` for the retired string, which was true of the page at that moment; the discrepancy was
  the deploy landing in between, and the re-measurement is what closed the redeploy row above.
- [x] **`201` + replay `duplicate:true` proven on the public URL.** Recorded 2026-09-29 from the run
  made against `https://sentinel.novatechsystem.co.uk` with the deployed `SENTINEL_INGEST_TOKEN` —
  a credential this QA pass deliberately never read (names, not values), so the run is the token
  holder's evidence, transcribed here rather than reproduced here:
  - first ingest: `HTTP 201`, `event_id: novaops-public-demo-001`,
    `incident_id: inc_a670b4d08a1848e997c4ed006e2842da`, `workflow_state: awaiting_approval`,
    `duplicate: False`;
  - replay of the same `event_id`: `HTTP 200`, the **same** `incident_id`, `duplicate: True`;
  - the console opened that incident through `/?incident=inc_a670b4d08a1848e997c4ed006e2842da`, and
    the audit trail reads `Operational event ingested` → `Incident analyzed` →
    `Human approval requested`.
  What this pass could verify independently is only the shape and the route: the incident id matches
  the documented `^inc_[0-9a-f]{32}$`, and `POST /api/v1/events/ingest` still answers `401` without a
  bearer token. **The stored incident itself is no longer retrievable** — a follow-up
  `GET /api/v1/incidents/inc_a670b4d08a1848e997c4ed006e2842da` returns `404`, which is the documented
  in-process-memory limit (`README.md:331` "a restart clears it",
  `docs/architecture/approval-workflow.md:178-179` "`POST /execute` on a restarted instance is a 404"),
  not a contradiction of the run. No timing for these two
  calls is recorded, because none was measured: the measured latency band in §4 is from the six local
  runs, and this document does not extend it.

## 4. NVIDIA integration

- [x] Live inference through the organiser's provided endpoint:
  `https://integrate.api.nvidia.com/v1` (`sentinel/nvidia.py:18`) with
  `nvidia/nemotron-3.5-lightning-30b-a3b` supplied as `NVIDIA_MODEL` (`nvidia.py:97`, no default).
- [x] Structured output enforced by a pinned forced tool call `submit_incident_assessment`,
  `temperature 0.1`, `top_p 0.9`, `max_tokens 4096` (`nvidia.py:140-143`); the payload is validated
  by pydantic, and an out-of-enum severity is a provider error rather than a guess.
- [x] Only `tool_calls[0].function.arguments` is read; `content` and `reasoning_content` are never
  surfaced (`nvidia.py:4`, asserted in `tests/test_console.py::test_ui_does_not_fake_progress_or_read_hidden_reasoning`).
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
  the local machine-first run, and since TASK-015A the transcribed **public production** ingest run
  under *Proven on production*, with what remains unmeasured there (its latency) split out under
  *Not yet measured*.
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
  never converge against itself. Result: **0 secret values.** The mention census — the scanned lines
  that merely *name* a variable or pattern — is counted in that report rather than here, because a
  per-line count moves when a scanned paragraph is re-wrapped. Six lines hold a fixed string in the
  value position and are listed one by one with their reason (empty placeholder, two `...` ellipses,
  an f-string header, a regex source, a Mermaid cell). Eight more carry a run-time generator, a shell
  reference, or the guard's own assertion string rather than a stored value, and each of those is
  named by file and line as well. PEM, `AKIA…`, `ghp_…`/`github_pat_…` all **0**, in the tree and in
  history.
- [x] History swept with the same patterns over **all of `git log --all -p`** → **0**, re-run after
  this pack landed and after each later docs commit. The diff's own size is deliberately not quoted
  here: commit count, diff bytes and added-line count grow with every commit, while the `0` does
  not, because the pack adds no *new* text to scan — the lines it appends are the documents the tree
  sweep above already covers one by one.
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
- [x] **Record the video.** **DONE** — recorded, reviewed and exported. Duration **2:29**, which is
  1 s under the floor of the 2:30–2:50 band above; that band was our editorial target, not a
  published rule (`requirements.md` #12 still has the real cap as `UNKNOWN`).
- [x] **Watch it end to end** at 100 % zoom on a laptop-sized window, confirming the coverage table
  in `video-shot-list.md` line by line. **DONE — attested by the operator** during the editing pass.
  A repository cannot see a video frame, so this line is a recorded human attestation rather than a
  measurement made here, and `video-review-checklist.md` keeps its per-item boxes unticked for the
  same reason.
- [x] **Upload / publish.** **DONE** — hosted on **YouTube**, visibility **unlisted**, title **“NovaBrain
  Sentinel — NVIDIA Claw Agent Challenge: London Demo”**, at <https://youtu.be/bQLiWO1G5Mw>. The link
  resolves for a request carrying no session: `oEmbed` returns `200` with that title and author
  `NovaTech Systems Group`, and the watch page returns `200` with `lengthSeconds` `148` and **0**
  occurrences of the "Sign in to confirm" interstitial. Visibility is the uploader's setting, recorded
  as stated; nothing in this tree can read it back.
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

## 11. Final smoke test before submitting

Production serves the code in this tree, including the `static/index.html:124` wording TASK-015A
changed — the deploy that carries it has happened, measured 2026-09-29 against `16d20e6` by hashing
the three served `static/` files against the committed ones. All items below were therefore run
against the live page. The video has since been recorded against that same URL, and the one line
still open here — the cold console run — stays open by policy, not by oversight: TASK-018 forbids
production inference, so no command in this pass can create the run it asks for.

- [x] `GET /` 200, rendering `Event-driven operational agent` with the London eyebrow; **0** hits for
  either retired string.
- [x] `/health` → `{"status":"ok","service":"novabrain-sentinel"}`. Re-measured in the TASK-018
  read-only pass: `200` with that exact body.
- [ ] One cold console run: *Run Demo Incident* → `high` → gate → refuse → approve → execute →
  `VERIFIED`. §3 records the live console QA already done (both viewports, 0 JS errors, the
  deliberate blocked attempt). `recording-runbook.md` §D films the demo through the producer path and
  then the console panels, so what this line still wants is the console's own *Run Demo Incident*
  button driven once, live, immediately before the form is submitted — a MANUAL action requiring no
  token (the console route is unauthenticated by design), and not something this documentation pass
  may trigger.
- [x] One machine run against the public URL: `201`, open `/?incident=<id>`, replay → `200
  duplicate:true` with the same incident id. **Done** — §3 records the transcript of the run made
  with the deployed `SENTINEL_INGEST_TOKEN` (`novaops-public-demo-001` →
  `inc_a670b4d08a1848e997c4ed006e2842da`, replay `duplicate:true`, same incident id). A recording-day
  re-run is optional, not required: it would create a second production incident to prove what is
  already proven, and the stored incident from the recorded run is gone with the process that held it
  (see §3), so a fresh run cannot reproduce that transcript — only a new one.
- [x] Secret sweep over the served responses (`/`, `/openapi.json`, `/static/app.js`): **0** hits
  for the documented pattern set.
- [ ] `git rev-parse HEAD` equals `git rev-parse origin/main`, working tree clean. Verified at the
  moment of writing; re-run after the final commit, since this document cannot quote the SHA of the
  commit that carries it.
- [x] **New in TASK-015A, closed in TASK-017:** re-fetch `GET /` and confirm the empty state reads
  "allow up to 90s" with **0** hits for the retired `takes about` range. Measured on the served page
  2026-09-29: `grep -c 'allow up to 90s'` → `1`, `grep -c 'takes about'` → `0`, and the whole file
  hashes the same as `static/index.html` in the tree. The recording-day fallback of running a
  container locally was not needed, so the video was made against the public URL.

## Blocked

- [x] Nothing in this task is blocked by the code. The one item that used to be — proving `201` +
  replay `duplicate:true` on the public URL, which needed the deployed `SENTINEL_INGEST_TOKEN` this
  pack deliberately never reads (names, not values) — is closed in §3 by the token holder's run, and
  reading a production secret to tick a box is still not how it gets closed here.
- [x] The registration-gated rules (§1) stay **UNKNOWN** until someone opens the form.
