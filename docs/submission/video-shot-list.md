# Video Shot List — 17 shots

TASK-015 §6. Pairs with [`video-script.md`](video-script.md) (narration) and
[`demo-scenario.md`](demo-scenario.md) (the 15 operator steps). Shots are numbered in **edit
order**, so `S01…S16` also run in timecode order (`S14b` sits inside the S14 window); the `step`
each refers to is a row of the demo-scenario table.

Recording setup for every browser shot: 1440 × 900 viewport, zoom 100 %, DevTools closed except
where a shot asks for it, browser chrome cropped out of the exported frame, window recording only
(no full-desktop capture, so no bookmarks bar, no other tabs, no notification pop-ups).

## Legibility rule

Judges watch on laptops and phones. Any string marked **MUST BE READABLE** below is a failure if it
is legible only when paused at 200 %. For those shots the plan is explicit: **record wide, then
punch in** — either browser zoom at 150–175 % before recording, or a 2–2.5× crop in the edit
centred on the target string, held ≥ 2 s. Never solve legibility by shrinking the surrounding UI.

| String | Where it lives | How it is made readable |
|---|---|---|
| `sentinel.novatechsystem.co.uk` | address bar | S01 crops the address bar; S16 re-states it as large end-card text |
| `workflow_state: awaiting_approval` | terminal | S07 punch-in on the five printed fields |
| `nvidia/nemotron-3.5-lightning-30b-a3b` | panel 2, model line | S09 with browser zoom 175 %, then hold a punch-in |
| `approval_required` | 409 response body, then the audit row's details line | S11 (DevTools) and S12 (audit row) |
| `execution_blocked` | **API JSON only** — the console prints its UI label (`app.js:19-27`) | S12 (terminal `curl`, raw token) |
| `event_ingested` | **API JSON only**, first element of `audit_trail` | S14b (terminal `curl`, raw tokens) |
| `SIMULATED ACTION` | badge, `static/index.html:105` | S10 and S13 keep the badge in the same frame as the control |
| `VERIFIED` + `Simulation: YES · simulated` | panel 5, `static/app.js:431,434` | S14 wide shot, label never cropped |
| `duplicate: True` + the same `incident_id` | terminal | S15 split crop of both runs, monospace, unedited |

Two of the eleven required strings are raw audit tokens, and the console deliberately never renders
them: `renderAudit` maps every event through `AUDIT_LABELS` (`static/app.js:457`), so on screen
`event_ingested` reads "Operational event ingested" and `execution_blocked` reads "Execution
blocked by policy". The raw spellings therefore have to come from `GET /api/v1/incidents/<id>` in a
terminal. That is not a workaround — it is the honest split between the machine contract and the
human view, and it is the reason S12 and S14b exist.

## Shots

### S01 — Cold open, the live URL  ·  0:00–0:15  ·  browser
- **Action:** page already loaded at `https://sentinel.novatechsystem.co.uk`; cursor idles.
- **Visible evidence:** the public demo URL in the address bar; the empty-state line saying a real
  model call takes tens of seconds (`static/index.html:124`); the eyebrow naming the competition
  (`static/index.html:13`).
- **Narration:** block 1 (problem + pitch).
- **Risk / fallback:** cleared 2026-09-29 — production serves the corrected eyebrow and subtitle, and
  `static/index.html` hashes the same served as committed, so this shot can be filmed against the
  public URL as written. If a later deploy regresses it, reshoot rather than fix it in post.
- **Number caution:** `static/index.html:124` currently renders "about 15–50 seconds", which is wider
  than the measured 6.7–47.1 s (`claims-audit.md`, *Found, deliberately not edited*). Narrate the
  elapsed time you actually watch, never the printed range. The served page carries that same stale
  range, so the frame will show it — an edit to the line needs its own commit and deploy, and until
  one lands nothing changes what S01 can show.

### S02 — The disclosure badge  ·  ~0:12  ·  browser, punch-in
- **Action:** hold on the footer badge.
- **Visible evidence:** `Real NVIDIA inference · Safe simulated remediation`
  (`static/index.html:179`) — MUST BE READABLE.
- **Narration:** the bold sentence of block 1 lands on this frame.
- **Risk / fallback:** if the badge sits below the fold at 900 px height, scroll to it before
  recording; never overlay it in post.

### S03 — Architecture, one diagram  ·  0:15–0:35  ·  browser or slide
- **Action:** slow pan left→right across the single Mermaid flow in
  `docs/submission/architecture.md`.
- **Visible evidence:** producer → `POST /api/v1/events/ingest` → bearer guard → idempotency
  ledger → NVIDIA Nemotron → policy → state machine → approval branch → simulated action →
  verification → audit → console; the real/simulated/not-implemented classes, plus the loop strip
  and its legend (`static/index.html:27-44`) reading `Approval: REAL` and `Action: SIMULATED`.
- **Narration:** block 2.
- **Risk / fallback:** if the diagram renders too small, show the loop strip instead and leave the
  diagram for the README — never a hand-drawn simplification of it.

### S04 — Terminal: the producer command  ·  0:35–0:45  ·  terminal
- **Action:** type and run `python scripts/send_demo_event.py --url https://sentinel.novatechsystem.co.uk`.
- **Visible evidence:** the command line, with **no token value in it** and no
  `export …=<value>` in the visible scrollback above it.
- **Narration:** "We are not typing. This is the producer's contract…"
- **Risk / fallback:** clear the scrollback (`clear`) before recording if the earlier `export` is
  visible. Never type the token on camera — the script reads it from the environment
  (`scripts/send_demo_event.py:78`).

### S05 — The event payload  ·  0:45–0:55  ·  editor pane or GitHub blob
- **Action:** show `scripts/send_demo_event.py:31-45` — `source: novaops`,
  `event_type: ram_high`, `title: API latency spike`, `severity_hint: warning`, three evidence
  lines.
- **Visible evidence:** the input as a checked-in file, so the payload is reproducible from the
  repo rather than typed live.
- **Narration:** "…p95 latency from a hundred and eighty milliseconds to two point four seconds.
  The hint says warning. Only a hint."
- **Risk / fallback:** if the file view is too small to read, open the blob on GitHub — that also
  pre-seeds the repository shot.

### S06 — The wait, honestly  ·  inside the 0:55 boundary  ·  terminal
- **Action:** request in flight; cut after ~1.5 s with the caption `waiting on the model — real`.
- **Visible evidence:** the pending command and a visible elapsed-time readout.
- **Narration:** none over the cut.
- **Risk / fallback:** real latency is 6.7–47.1 s. Cut it and caption it; a long silent hold is the
  one thing this shot must not become. The response itself is never substituted.

### S07 — `HTTP 201` and the five fields  ·  0:55–1:05  ·  terminal, punch-in
- **Action:** the response arrives (demo-scenario step 3).
- **Visible evidence:** `HTTP 201`, `event_id: novaops-demo-0001`, `incident_id: inc_…`,
  `workflow_state: awaiting_approval`, `duplicate: False`, `console_path: /?incident=inc_…`.
  MUST BE READABLE: `workflow_state` and the incident id.
- **Narration:** "**[read from screen]** seconds later, the answer lands."
- **Risk / fallback:** `401` → wrong token; `503 ingest_not_configured` → the deployed runtime has
  none. `workflow_state: analyzed` means the model rated this below `high` — re-run once, then use
  fallback incident 1.

### S08 — Open the incident by URL  ·  1:05–1:12  ·  browser
- **Action:** paste `<demo-url>/?incident=<incident_id>` (step 4).
- **Visible evidence:** the `?incident=` bridge loading panel 1 with the producer's event — not a
  typed question.
- **Narration:** "It came from the producer, and this link is the whole hand-off."
- **Risk / fallback:** if the loading line (`static/app.js:567` area) persists, the id is off by a
  character — re-copy it from the terminal.

### S09 — The assessment  ·  1:12–1:20  ·  browser, panel 2
- **Action:** scroll to panel 2 (steps 6 and 8).
- **Visible evidence:** `severity: high`, the confidence value, `requires_approval: true`, the
  one-sentence rationale, and the model name on the model line (`static/index.html` panel 2,
  populated from `ModelInfo`). MUST BE READABLE: `nvidia/nemotron-3.5-lightning-30b-a3b`.
- **Narration:** block 4, including "only the validated tool arguments reach this page".
- **Risk / fallback:** if the model name is truncated, use browser zoom; do not add it as a text
  overlay. If the confidence differs from the 0.86–0.87 measured range, keep it — narration reads
  it from screen.

### S10 — The gate  ·  1:20–1:28  ·  browser, panel 3
- **Action:** frame panel 3 while the incident is `awaiting_approval`.
- **Visible evidence:** the ⚠ HUMAN APPROVAL REQUIRED state; *Execute simulated action* visibly
  disabled while *Attempt Execution* is enabled (`static/app.js:472-476`); the safety line
  (`static/index.html:117`); the `Approval: REAL` chip; the `SIMULATED ACTION` badge in the same
  frame.
- **Narration:** "Now the part that is not a model opinion… that floor is written in code, not in
  a prompt."
- **Risk / fallback:** if the gate is absent, severity was below `high` — see S07's fallback.

### S11 — Attempt execution, get refused  ·  1:28–1:40  ·  browser + DevTools Network
- **Action:** click *Attempt Execution* (`#btn-attempt`) **before** approving (step 10).
- **Visible evidence:** the banner "Execution blocked by Sentinel policy — Approval is required
  before this action can run.", and DevTools showing status `409` with
  `"reason": "approval_required"`. MUST BE READABLE: `approval_required`.
- **Narration:** "So I press execute before approving. Four hundred and nine — approval required."
- **Risk / fallback:** the red 409 line in Chrome's console stays in frame; it is evidence, not a
  glitch. A `200` here is a product defect — stop filming and report it, do not re-shoot around it.

### S12 — The refusal is an audit event  ·  1:40–1:45  ·  browser punch-in, then terminal
- **Action:** scroll panel 6 to the new row (step 11), then show the same row as JSON from a
  terminal: `curl -s https://sentinel.novatechsystem.co.uk/api/v1/incidents/<incident_id>`.
- **Visible evidence:** in the browser, the row "Execution blocked by policy", actor `operator`,
  details `action: scale_api_replicas · reason: approval_required`; in the terminal, the same entry
  with its raw event name `execution_blocked`. MUST BE READABLE: `execution_blocked`.
- **Narration:** "The refusal is written into the audit trail."
- **Risk / fallback:** if the row is missing, the audit leg is broken — do not narrate over an
  absent row. The console never prints the raw token, so a browser-only take cannot satisfy the
  legibility rule for S12; the `curl` frame is mandatory, not optional.

### S13 — Approve, then execute  ·  1:45–2:05  ·  browser
- **Action:** click *Approve* (`#btn-approve`), then *Execute simulated action* (`#btn-execute`)
  (step 12).
- **Visible evidence:** `approval_granted` with the operator recorded; `state: approved` then
  `executing`; the `SIMULATED ACTION` label still on screen during execution.
- **Narration:** block 6, including "There is no orchestrator behind this route, and the console
  says so instead of letting me imply it."
- **Risk / fallback:** if *Execute* stays disabled after approving, the approval did not record —
  reshoot the sequence; do not double-click and keep the second.

### S14 — Verification and the full trail  ·  2:05–2:25  ·  browser
- **Action:** panel 5 first, then panel 6 end to end (steps 13 and 14).
- **Visible evidence:** `VERIFIED` with `Simulation: YES · simulated`; the before→after metrics
  exactly as returned (replicas, p95, error rate, restarts); the eight audit rows in append order,
  as the console words them — *Operational event ingested → Incident analyzed → Human approval
  requested → Execution blocked by policy → Operator approved → Simulated action requested →
  Simulated action finished → Outcome verified*. MUST BE READABLE: the first row and the row order.
- **Narration:** block 7.
- **Edit note:** if the scroll through panel 6 runs long, speed-ramp it; do not jump-cut the middle
  of the list, because the visible order is the claim.
- **Risk / fallback:** fewer than eight rows means a step was skipped — re-shoot from S11 so the
  trail is complete.

### S14b — The trail as the API sees it  ·  inside the S14 window  ·  terminal, punch-in
- **Action:** `curl -s https://sentinel.novatechsystem.co.uk/api/v1/incidents/<incident_id>` and
  show `audit_trail` (demo-scenario step 14b).
- **Visible evidence:** the eight raw event tokens in order — `event_ingested`,
  `incident_analyzed`, `approval_requested`, `execution_blocked`, `approval_granted`,
  `execution_requested`, `execution_finished`, `verification_recorded` — each with its `actor` and
  timestamp. MUST BE READABLE: `event_ingested`.
- **Narration:** "This is the same trail the page is showing, in the words the backend wrote."
- **Risk / fallback:** if the JSON holds seven entries, the incident came from the console form and
  not the producer — the machine path was not exercised. Re-run S04 rather than narrating over it.

### S15 — Replay: the same event, twice  ·  2:25–2:40  ·  terminal, split crop
- **Action:** re-run the identical command from S04 (step 15).
- **Visible evidence:** `HTTP 200`, `duplicate: True`, the **same** `incident_id` as S07,
  `workflow_state: verified`, and the wall time (~20 ms) beside the first call's ~10 s.
  MUST BE READABLE: `duplicate: True`.
- **Narration:** block 8.
- **Risk / fallback:** a second `201` means the ledger lost the claim (a restart, or a second
  replica). Say so on camera and treat it as evidence of the in-memory boundary — do not hide it.

### S16 — End card: repository and demo  ·  2:40–2:50  ·  browser, then card
- **Action:** open the public GitHub repository, then cut to the end card.
- **Visible evidence:** `github.com/novatechsystemsgroup/novabrain-sentinel` showing the README
  first screen (live-demo line and the loop table); then the card with both URLs at legible size.
- **Narration:** block 9.
- **Risk / fallback:** if the repository **description** still reads "Persistent Operational AI
  Agent", it contradicts the claims audit — fix it first (manual action, tracked in
  `checklist.md`), otherwise the last frame undercuts the whole video.

## Coverage check — every required piece of visible evidence

| Required evidence | Shot(s) |
|---|---|
| Public demo URL | S01, S16 |
| NVIDIA model name | S09 |
| `event_ingested` (raw token) | S14b |
| `approval_required` | S11, S12 |
| `execution_blocked` (raw token) | S12 |
| Operator approval | S13 |
| `SIMULATED ACTION` label | S10, S13 |
| `VERIFIED` result | S14 |
| Full audit trail | S14 (labels), S14b (raw JSON) |
| `duplicate: true` replay | S15 |
| GitHub repository | S16 |
| "Real NVIDIA inference. Safe simulated remediation." spoken | S02 |

If any row of this table is missing from the rough cut, the cut is not finished.
