# Recording Runbook — Final Video Take

TASK-016. **The take is done.** Recorded, exported at **2:29**, uploaded to YouTube (unlisted) at
<https://youtu.be/bQLiWO1G5Mw> under the title **NovaBrain Sentinel — NVIDIA Claw Agent Challenge:
London Demo**. This file is kept as the operational record of how the video was made, not as
instructions still to follow: sections A–E are the preparation the take was filmed from, and a box
left unticked in them is a check that cannot be re-run from a repository after the fact. §F and §G
below separate what TASK-018 measured from what it could not. Do not treat this as a second script.

References:
- [`video-script.md`](video-script.md) — narration blocks
- [`video-shot-list.md`](video-shot-list.md) — 17 shots in edit order
- [`demo-scenario.md`](demo-scenario.md) — the 15 operator steps

## A. Before recording

### Prerequisites

- [x] **Recording target: the public URL.** This used to be an open decision. Production now serves
  the corrected copy — measured 2026-09-29 against `16d20e6`, the served `static/index.html` hashes
  byte-for-byte the same as the committed file, `grep -c 'allow up to 90s'` on the live page returns
  `1` and `grep -c 'takes about'` returns `0` (see [`checklist.md`](checklist.md) §2 and §11 for the
  three hashes). So film against `https://sentinel.novatechsystem.co.uk`, and shot **S01 is safe**.
  The local QA container (`sentinel-qa-015a` on `127.0.0.1:18123`) that an earlier revision of this
  runbook offered as the fallback is no longer needed; if you have it running, stop it and remove it
  so there is only one page on screen.
- [x] **GitHub repo description updated.** It reads "Event-driven operational agent — NVIDIA Claw
  Agent Challenge: London", set and read back through the GitHub API on 2026-09-29. The last frame of
  the video shows the repo, and this is the string the claims audit uses; re-check with
  `gh repo view novatechsystemsgroup/novabrain-sentinel -q .description` if anything looks off.
- [x] **Health check passes.** `GET https://sentinel.novatechsystem.co.uk/health` → `200` with
  `{"status":"ok","service":"novabrain-sentinel"}`. Re-measured 2026-09-29 in the TASK-018 read-only
  pass: `200`, that exact body.
- [x] **Homepage copy verified.** `GET /` contains:
  - "NVIDIA Claw Agent Challenge: London" (eyebrow)
  - "Event-driven operational agent" (subtitle)
  - "Real NVIDIA inference"
  - "Safe simulated remediation"
  - "Approval: REAL"
  - "Action: SIMULATED"
  - "LEARN" + "not implemented" (the chip serves `LEARN &middot; not implemented`, so the contiguous
    string `LEARN not implemented` greps `0` — that is markup, not a missing label)
  - "allow up to 90s" (the corrected wait copy, not the old "15–50 seconds") — re-measured
    2026-09-29 against the served page: `NVIDIA Claw Agent Challenge: London`,
    `Event-driven operational agent`, `Real NVIDIA inference`, `Safe simulated remediation`,
    `Approval: REAL`, `Action: SIMULATED`, `LEARN` and `allow up to 90s` each return `1` hit,
    `not implemented` returns `2`, and `grep -c "takes about"` returns `0`.
- [ ] **Fresh event id chosen.** Use `novaops-video-demo-001` for the video take. Before filming,
  confirm this exact id has NOT already been used since the current production process started. If
  it has, pick a different fresh id (e.g., `novaops-video-demo-002`). *(A pre-take step: the id used
  on camera lives in the operator's terminal session, and this runbook never records token values,
  so it is not written down here.)*
- [ ] **Ingest token ready.** `SENTINEL_INGEST_TOKEN` is exported in the terminal session only.
  Never type it on camera. Never display it. The script reads it from the environment
  (`scripts/send_demo_event.py:78`), so no token value ever exists in a visible command line.

### Timing

- Target: **2:30–2:50** (self-imposed, not the organiser's official limit — that is UNKNOWN until
  the registration form is opened).
- Recorded outcome: **2:29** as the uploader states it, which sits 1–2 s under the floor of our own
  band (the published page's duration fields read about 148 s; see
  [`video-review-checklist.md`](video-review-checklist.md) for the reading). The band was an editorial
  target we set ourselves, so the take was kept rather than padded; re-cut only if the form turns out
  to state a minimum.
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

The time ranges in the shot headings are **edit-plan estimates written before the take existed**. The
exported video is 2:29, so the last two headings (2:25–2:40 and 2:40–2:50) overrun the finished cut:
the replay beat and the end card are in the final seconds of the video, and their exact frame times
are not recorded here because a repository cannot read them off a frame.

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
- The exported take is **2:29** as the uploader states it. The published page is a second shorter —
  its duration fields read 147,999–148,050 ms and its two `lengthSeconds` values are 148 and 149 —
  so the same cut reads as 2:28 or 2:29 depending on which one you open
  ([`video-review-checklist.md`](video-review-checklist.md) holds the measurement).
- If shortening is needed, trim SHOT 2 (the loop strip) and SHOT 13 (the audit trail scroll)
  first. Never cut the blocked-execution beat (SHOT 9).

## F. Final review

Before marking the video as done:

- [x] **Watch the full export from beginning to end** at 100% zoom on a laptop-sized window.
  **Attested by the operator** in the editing pass and recorded in [`checklist.md`](checklist.md) §9;
  no repository command can watch a video, so this line rests on the uploader's word rather than on
  a measurement made here.
- [x] **Verify duration** is within target (2:30–2:50 or the form's cap if different). **Measured:
  2:29** as the uploader states it — 1–2 s under the floor of a band we set ourselves, with the
  organiser's cap still `UNKNOWN`.
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
- [x] **Upload / publish** at whatever host the form asks for (UNKNOWN until registered). Uploaded to
  **YouTube** as **unlisted** at <https://youtu.be/bQLiWO1G5Mw>. If the Airtable form turns out to
  require a different host, this link still identifies the take; re-hosting is a post-form action.
- [x] **Verify the uploaded link** while signed out / in incognito mode. Verified by the same
  session-less requests measured in §G: `oEmbed` `200` with the correct title, watch page `200` with
  no sign-in interstitial.
- [x] **Only then mark the video as DONE.** TASK-018 marks **recording complete**, **upload
  complete** and **public share link exists** as DONE. The competition entry itself is not: the
  Airtable form has not been submitted.

## G. Upload validation

- [x] **Confirm the video plays for a signed-out visitor** (not just while logged in). Measured
  against the published link on 2026-09-29 from a request carrying no session: the watch page answers
  `200`, serves a player whose payload carries `"videoId":"bQLiWO1G5Mw"`, and returns **0**
  occurrences of the "Sign in to confirm you're human" interstitial, and YouTube's `oEmbed` endpoint
  answers `200` with the title and author `NovaTech Systems Group`. That is the reachable-signed-out
  proxy, not an incognito play-through from a browser this repository does not control.
- [ ] **Confirm the video URL is stable** (not a temporary link that expires). Unticked on purpose:
  `youtu.be/bQLiWO1G5Mw` is a canonical YouTube video id, not a signed or expiring URL, but its
  permanence depends on the uploading account, which no command here can inspect. Re-check it on the
  day the form is filled.
- [x] **Record the video URL for the submission form.**
  <https://youtu.be/bQLiWO1G5Mw> — title **NovaBrain Sentinel — NVIDIA Claw Agent Challenge: London
  Demo**, runtime **2:29**, host **YouTube**, visibility **Unlisted**. The URL is now carried by
  [`README.md`](../../README.md), [`JUDGE-QUICKSTART.md`](JUDGE-QUICKSTART.md),
  [`submission-copy.md`](submission-copy.md), [`checklist.md`](checklist.md) and
  [`status.md`](status.md).

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

Kept as the record of the gate the take was filmed from. The boxes below describe a moment that has
passed — a clean terminal, a chosen event id, recording software armed — and cannot be re-run from a
repository afterwards. The two that a later read-only pass *could* re-measure, health and homepage
copy, were re-measured on 2026-09-29 and are ticked with their results in §A rather than here.

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
[`video-review-checklist.md`](video-review-checklist.md). It was the gate after editing and before
upload; since the upload happened, that file also carries the published artefact table (title,
runtime, host, visibility, URL) and states which of its own boxes a later pass could not re-verify.

## GitHub description status

Check whether the public GitHub repository description has been manually changed to:

> Event-driven operational agent — NVIDIA Claw Agent Challenge: London

If not, report it as a human action. Do not attempt account-setting changes unless explicitly
authorised.

Done: TASK-017 set that description through the GitHub API and read the value back. It is a
site-level field rather than a file, so it is worth re-checking on the day the form is filled.

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
