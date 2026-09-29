# Recording Runbook — Final Video Take

TASK-016. This is the execution guide for recording the competition video. It turns the existing
script, shot list and demo scenario into an operational workflow. Read this on recording day; do
not treat it as a second script.

References:
- [`video-script.md`](video-script.md) — narration blocks
- [`video-shot-list.md`](video-shot-list.md) — 17 shots in edit order
- [`demo-scenario.md`](demo-scenario.md) — the 15 operator steps

## A. Before recording

### Prerequisites

- [ ] **Redeploy decision made.** Production served the pre-TASK-015A copy ("takes about 15–50
  seconds") as of 2026-09-29. The tree now says "allow up to 90s". You have two options:
  - **Option 1:** Deploy first, then record against `https://sentinel.novatechsystem.co.uk`. The
    live page then matches the tree, and S01 in the shot list is safe to film.
  - **Option 2:** Record against the local QA container (`sentinel-qa-015a` on `127.0.0.1:18123`,
    built from the current tree, serving the corrected copy). The video then shows a localhost URL,
    which is honest but less impressive than the public demo.
  - **Do not** record against the public URL if it still serves the old sentence — that would show
    a judge a false promise in the empty state.
- [ ] **GitHub repo description updated.** It should read "Event-driven operational agent — NVIDIA
  Claw Agent Challenge: London" (or similar). If it still says "Persistent Operational AI Agent",
    fix it in repository settings before recording — the last frame of the video shows the repo,
    and a contradictory description undercuts the claims audit.
- [ ] **Health check passes.** `GET https://sentinel.novatechsystem.co.uk/health` → `200` with
  `{"status":"ok","service":"novabrain-sentinel"}`. If recording against the local container, use
  `http://127.0.0.1:18123/health` instead.
- [ ] **Homepage copy verified.** `GET /` contains:
  - "NVIDIA Claw Agent Challenge: London" (eyebrow)
  - "Event-driven operational agent" (subtitle)
  - "Real NVIDIA inference"
  - "Safe simulated remediation"
  - "Approval: REAL"
  - "Action: SIMULATED"
  - "LEARN not implemented"
  - "allow up to 90s" (the corrected wait copy, not the old "15–50 seconds")
- [ ] **Fresh event id chosen.** Use `novaops-video-demo-001` for the video take. Before filming,
  confirm this exact id has NOT already been used since the current production process started. If
  it has, pick a different fresh id (e.g., `novaops-video-demo-002`).
- [ ] **Ingest token ready.** `SENTINEL_INGEST_TOKEN` is exported in the terminal session only.
  Never type it on camera. Never display it. The script reads it from the environment
  (`scripts/send_demo_event.py:78`), so no token value ever exists in a visible command line.

### Timing

- Target: **2:30–2:50** (self-imposed, not the organiser's official limit — that is UNKNOWN until
  the registration form is opened).
- If the form reveals a different limit at submission time, re-cut to it; preserve the core safety
  sequence (blocked execution, approval, simulated action) even if the video must be shortened.

## B. Terminal preparation

- [ ] **Clean prompt.** Open a new terminal window. Run `clear` to empty the scrollback.
- [ ] **Large readable font.** Increase the terminal font size so commands are legible at 1080p.
- [ ] **No command history containing tokens.** Run `history -c` to clear the session history, or
  open a fresh shell. Confirm no earlier `export SENTINEL_INGEST_TOKEN=...` is visible in the
  scrollback.
- [ ] **No environment dumps.** Do not run `env`, `printenv`, or `echo $SENTINEL_INGEST_TOKEN` on
  camera.
- [ ] **No `.env` visible.** Do not `cat .env` or `ls -la` showing `.env` in frame.
- [ ] **No `docker inspect ...Env`.** Do not inspect container environment variables on camera.
- [ ] **Token loaded off-take.** Export the token before recording starts:
  ```bash
  export SENTINEL_INGEST_TOKEN=<value>
  ```
  Then clear the terminal or scroll past it before the camera rolls.

## C. Browser preparation

- [ ] **Clean window.** Close all other tabs. No bookmarks bar visible (or crop it out). No
  personal data, no private tabs, no password manager pop-ups.
- [ ] **Notifications disabled.** Turn off system notifications (macOS: System Settings →
  Notifications → Do Not Disturb, or disable per-app).
- [ ] **No DevTools unless deliberately used.** DevTools is only needed for S11 (the 409 network
  line) and S12 (the audit JSON). Keep it closed until those shots.
- [ ] **Zoom suitable for video.** 100% at 1440 × 900 is the default. If text is too small, use
  125–150% browser zoom, or record wide and punch in in the edit.
- [ ] **1440-ish desktop layout preferred.** The console is designed for 1440 × 900. If your screen
  is smaller, use the 390 × 844 mobile layout, but the desktop layout is preferable for the video.
- [ ] **No browser extensions covering content.** Disable ad blockers, grammar checkers, or any
  extension that overlays the page.
- [ ] **Cursor visible.** Ensure the cursor is visible and not hidden by a theme or extension.

## D. Recording sequence

The sequence below maps to the 13 shots in the brief. Each shot references the corresponding
narration block in [`video-script.md`](video-script.md) and the operator step in
[`demo-scenario.md`](demo-scenario.md).

### SHOT 1 — Public Sentinel console (0:00–0:15)

- **Action:** Page already loaded at the public URL (or `127.0.0.1:18123` if using the local
  container). Cursor idles.
- **Visible:** The public demo URL in the address bar; the empty-state line saying "allow up to
  90s"; the eyebrow "NVIDIA Claw Agent Challenge: London".
- **Narration:** Block 1 (problem + pitch). End with the bold sentence: **"Real NVIDIA inference.
  Safe simulated remediation."**

### SHOT 2 — Cognitive loop and real/simulated legend (0:12–0:15)

- **Action:** Hold on the footer badge or the loop strip in the console header.
- **Visible:** OBSERVE, UNDERSTAND, DECIDE, ACT / REQUEST APPROVAL, VERIFY, LEARN not implemented.
  The chip reads "Approval: REAL · Action: SIMULATED".
- **Narration:** "Real NVIDIA inference. Safe simulated remediation." (spoken, not just captioned)

### SHOT 3 — Terminal producer command (0:35–0:45)

- **Action:** Type and run:
  ```bash
  python3 scripts/send_demo_event.py \
    --url https://sentinel.novatechsystem.co.uk \
    --event-id novaops-video-demo-001
  ```
  (or `--url http://127.0.0.1:18123` if using the local container)
- **Visible:** The command line itself, with **no token value in it** and no `export …=<value>` in
  the visible scrollback above it.
- **Narration:** "We are not typing. This is the producer's contract…"

### SHOT 4 — The wait, honestly cut (inside the 0:55 boundary)

- **Action:** Request in flight. Cut after ~1.5 s with the caption "Real NVIDIA inference" or
  "waiting on the model — real".
- **Visible:** The pending command and a visible elapsed-time readout.
- **Narration:** None over the cut.
- **Note:** Real latency is 6.7–47.1 s. Cut the dead wait; do not leave a long silent hold. The
  response itself is never substituted.

### SHOT 5 — HTTP 201 and the five fields (0:55–1:05)

- **Action:** The response arrives (demo-scenario step 3).
- **Visible:** `HTTP 201`, `event_id: novaops-video-demo-001`, a new `incident_id: inc_…`,
  `workflow_state: awaiting_approval`, `duplicate: False`, `console_path: /?incident=inc_…`.
- **Narration:** "**[read from screen]** seconds later, the answer lands."
- **Note:** If `workflow_state` is `analyzed` instead of `awaiting_approval`, the model rated this
  below `high` — re-run once with a fresh event id, then use fallback incident 1 from
  `demo-scenario.md`.

### SHOT 6 — Open the incident in the browser (1:05–1:12)

- **Action:** Paste `<demo-url>/?incident=<incident_id>` in the browser (demo-scenario step 4).
- **Visible:** The incident loads by id; panel 1 shows the producer's event, not a typed question.
- **Narration:** "It came from the producer, and this link is the whole hand-off."

### SHOT 7 — The assessment (1:12–1:20)

- **Action:** Scroll to panel 2 (demo-scenario steps 6 and 8).
- **Visible:** `severity: high` (or `critical`), the confidence value, `requires_approval: true`,
  the one-sentence rationale, and the model name `nvidia/nemotron-3.5-lightning-30b-a3b`.
- **Narration:** Block 4. Read the confidence from the screen, not from this script.
- **Note:** If severity is below `high`, the approval gate will not appear — see the model
  variability rules below.

### SHOT 8 — The approval gate (1:20–1:28)

- **Action:** Frame panel 3 while the incident is `awaiting_approval`.
- **Visible:** The ⚠ HUMAN APPROVAL REQUIRED state; the `Approval: REAL` chip; the `SIMULATED
  ACTION` badge in the same frame.
- **Narration:** "Now the part that is not a model opinion… that floor is written in code, not in
  a prompt."

### SHOT 9 — Attempt execution, get refused (1:28–1:40)

- **Action:** Click *Attempt Execution* **before** approving (demo-scenario step 10).
- **Visible:** The banner "Execution blocked by Sentinel policy — Approval is required before this
  action can run." In the audit trail: `Execution blocked by policy`, actor `operator`, reason
  `approval_required`.
- **Narration:** "So I press execute before approving. Four hundred and nine — approval required."
- **Note:** This is one of the most important shots. Do not cut it. Chrome will log one red 409
  network line; leave it visible — it is evidence, not a glitch.

### SHOT 10 — Approve (1:40–1:45)

- **Action:** Click *Approve* (demo-scenario step 12).
- **Visible:** `Operator approved` in the audit trail.
- **Narration:** "I approve as the operator."

### SHOT 11 — Execute the simulated action (1:45–2:05)

- **Action:** Click *Execute simulated action* (demo-scenario step 12).
- **Visible:** The `SIMULATED ACTION` badge still on screen during execution. Never crop out the
  simulated label.
- **Narration:** "The allowlist is closed — two actions, both simulated."

### SHOT 12 — Verification (2:05–2:25)

- **Action:** Panel 5 (demo-scenario step 13).
- **Visible:** `VERIFIED`, `Simulation: YES`. The before → after metrics exactly as returned
  (replicas, p95, error rate, restarts).
- **Narration:** Read the numbers from the screen, not from this script. "Verification reads
  before and after. Replicas **[read from screen]**, p95 **[read from screen]**, error rate
  **[read from screen]**."

### SHOT 13 — Audit trail (2:05–2:25, continues)

- **Action:** Panel 6 scrolled so the full 8-event order is legible (demo-scenario step 14).
- **Visible:** The eight audit rows in append order:
  1. Operational event ingested
  2. Incident analyzed
  3. Human approval requested
  4. Execution blocked by policy
  5. Operator approved
  6. Simulated action requested
  7. Simulated action finished
  8. Outcome verified
- **Narration:** "And the incident history is one append-ordered trail — eight events, including
  the refusal."
- **Note:** Do not claim timestamp ordering; append order is authoritative.

### SHOT 14 — Replay: idempotency (2:25–2:40)

- **Action:** Return to the terminal and run the **same** command again:
  ```bash
  python3 scripts/send_demo_event.py \
    --url https://sentinel.novatechsystem.co.uk \
    --event-id novaops-video-demo-001
  ```
- **Visible:** `HTTP 200`, `duplicate: True`, the **same** `incident_id` as SHOT 5.
- **Narration:** "Same event id, same request. **[read from screen]** milliseconds later: duplicate
  true, same incident id. No second model call, no second incident."

### SHOT 15 — End card (2:40–2:50)

- **Action:** Cut to the end card.
- **Visible:**
  ```
  NovaBrain Sentinel
  https://sentinel.novatechsystem.co.uk
  https://github.com/novatechsystemsgroup/novabrain-sentinel
  ```
- **Narration:** "Sentinel is an event-driven operational agent with a hard human gate. Live demo
  and full source are public — links on screen."
- **Note:** Hold ≥ 3 s so the URLs are readable.

## E. Editing sequence

### Allowed

- Hard cuts between shots
- Crop / zoom for legibility (punch in on small text)
- Captions (e.g., "Real NVIDIA inference" over the wait cut)
- Removing the dead inference wait (SHOT 4)
- Tightening terminal/browser transitions
- Speed-ramping the scroll through the audit trail if it runs long

### Not allowed

- Replacing a real model response with a fabricated one
- Editing severity, confidence, or any model output
- Changing incident IDs
- Hiding the `SIMULATED` labels
- Pretending remediation was real
- Presenting old footage as the current run if values differ
- Exposing secrets and trying to blur them later — if a secret appears in frame, discard that take

### Duration

- Target: **2:30–2:50** unless the registration form reveals a different limit.
- If shortening is needed, trim SHOT 2 (the loop strip) and SHOT 13 (the audit trail scroll)
  first. Never cut the blocked-execution beat (SHOT 9).

## F. Final review

Before marking the video as done:

- [ ] **Watch the full export from beginning to end** at 100% zoom on a laptop-sized window.
- [ ] **Verify duration** is within target (2:30–2:50 or the form's cap if different).
- [ ] **Verify audio sync** — narration matches the visuals.
- [ ] **Verify every required piece of evidence** is present. Use the coverage table in
  [`video-shot-list.md`](video-shot-list.md) line by line:
  - Public demo URL
  - NVIDIA model name
  - `event_ingested` (raw token, from terminal `curl`)
  - `approval_required`
  - `execution_blocked` (raw token, from terminal `curl`)
  - Operator approval
  - `SIMULATED ACTION` label
  - `VERIFIED` result
  - Full audit trail
  - `duplicate: true` replay
  - GitHub repository
  - "Real NVIDIA inference. Safe simulated remediation." spoken
- [ ] **Verify no secrets are visible.** No NVIDIA key, no ingest token, no `.env`, no shell
  environment dump, no personal data, no private browser tabs, no passwords.
- [ ] **Verify no false claims.** No real-remediation claim, no production-NovaOps integration
  claim, no durable-persistence claim, no autonomous high/critical remediation claim, no fake
  timing claim.
- [ ] **Verify quality.** Text readable at normal laptop size, audio understandable, no long silent
  wait, no accidental notification, no mouse wandering, no terminal typo left visible, transitions
  understandable.
- [ ] **Upload / publish** at whatever host the form asks for (UNKNOWN until registered).
- [ ] **Verify the uploaded link** while signed out / in incognito mode.
- [ ] **Only then mark the video as DONE.**

## G. Upload validation

- [ ] Confirm the video plays for a signed-out visitor (not just while logged in).
- [ ] Confirm the video URL is stable (not a temporary link that expires).
- [ ] Record the video URL for the submission form.

## Model variability rules

The recording must tolerate real model variability.

- **Never depend on one exact sentence, one exact confidence, or one exact list of causes.**
  Narration says **[read from screen]** precisely so this is not a problem.
- **If severity is HIGH or CRITICAL:** continue normally.
- **If severity is LOW or MEDIUM and no approval gate appears:**
  - Do not fake an approval requirement.
  - Stop that take.
  - Run ONE fresh canonical stronger-evidence event (use a different event id, e.g.,
    `novaops-video-demo-002`).
  - Keep the real result.
  - If repeated unexpected behavior occurs, stop and report rather than fabricating.
- **Do not edit model output.** If a run is weak, re-run it or switch to the fallback incident.
  Cutting between takes is fine; fabricating a response is not.

## Screen recording settings (macOS)

### Preferred

- **Resolution:** 1920 × 1080 output if possible.
- **Frame rate:** 30 fps is sufficient.
- **Browser content:** Large enough to read at 100% on a laptop. Use 125–150% browser zoom if
  necessary.
- **Terminal font:** Enlarged so commands are legible.
- **Microphone:** Clean, no background noise.
- **Cursor:** Visible.
- **System notifications:** Disabled.

### Tools

- **macOS built-in screen recording** (Shift + Cmd + 5) is sufficient. It captures a selected
  window or the full screen, records at 30 fps, and exports to MP4.
- **QuickTime Player** (File → New Screen Recording) is an alternative.
- **Editing:** Use the simplest available workflow. macOS's built-in video editor (in QuickTime or
  Photos) can trim and cut. If more advanced editing is needed, use what is available — do not
  assume paid software.

## Pre-recording checklist (immediately before the take)

- [ ] `GET /health` → `200 OK`
- [ ] Homepage is the final build (corrected wait copy present)
- [ ] GitHub main is final (`git rev-parse HEAD` equals `git rev-parse origin/main`)
- [ ] No redeploy in progress
- [ ] Terminal is clean, token loaded off-take
- [ ] Browser is clean, notifications disabled
- [ ] Fresh event id chosen and confirmed unused
- [ ] Screen recording software ready, microphone tested

## The exact terminal command for the take

```bash
python3 scripts/send_demo_event.py \
  --url https://sentinel.novatechsystem.co.uk \
  --event-id novaops-video-demo-001
```

The ingest token must already exist in the terminal environment. Never show how it was loaded.
Never type it on camera. Never display it.

## Secret-handling safeguards

- `SENTINEL_INGEST_TOKEN` is exported in the terminal session only, never in a command line, never
  in a file that gets committed.
- The script reads it from the environment (`scripts/send_demo_event.py:78`), so no token value
  ever exists in a visible command line or shell history.
- Clear the terminal scrollback before recording if the earlier `export` is visible.
- If a secret ever appears in frame: discard that take, not just the frame.

## Browser recording order

1. Public Sentinel console (SHOT 1)
2. Cognitive loop and real/simulated legend (SHOT 2)
3. Open the incident by URL (SHOT 6)
4. The assessment (SHOT 7)
5. The approval gate (SHOT 8)
6. Attempt execution, get refused (SHOT 9)
7. Approve (SHOT 10)
8. Execute the simulated action (SHOT 11)
9. Verification (SHOT 12)
10. Audit trail (SHOT 13)

Terminal shots (SHOT 3, SHOT 4, SHOT 5, SHOT 14) are interleaved as needed.

## Narration status

The narration is written in [`video-script.md`](video-script.md) and summarized in
[`narration-cheatsheet.md`](narration-cheatsheet.md). Every number on screen is on-screen text;
nothing is asserted only in narration. Where the script says **[read from screen]**, read the
number from the screen, not from this document.

## Review checklist status

The final video review checklist is in
[`video-review-checklist.md`](video-review-checklist.md). Use it after editing, before upload.

## GitHub description status

Check whether the public GitHub repository description has been manually changed to:

> Event-driven operational agent — NVIDIA Claw Agent Challenge: London

If not, report it as a human action. Do not attempt account-setting changes unless explicitly
authorised.

## Files changed by TASK-016

- `docs/submission/recording-runbook.md` (this file)
- `docs/submission/narration-cheatsheet.md`
- `docs/submission/video-review-checklist.md`

No application code changed. No deployment performed.

## Commit

```
docs: prepare final Sentinel video recording
```

Push to main. Do NOT deploy. Do NOT modify application code.
