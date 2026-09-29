# Video Script — recorded at 2:29 against a verified 3-minute cap

TASK-015 §5. One take, one scenario: the canonical machine-first event in
[`demo-scenario.md`](demo-scenario.md). Narration is written to be read verbatim, except where it
says **[read from screen]** — those numbers must come from the recording, never from this file.

## Duration rule — VERIFIED from the official submission form

The submission form, opened by the submitter on 2026-09-29, answers this directly. Its field
**"Demo Video URL or Project Link"** reads, verbatim:

> "Show us your long-running agent in action! Submit either a demo video (up to 3 minutes; 30–90
> seconds preferred) or a link to your project where we can explore what you built. For videos,
> please use YouTube or Loom."

That is quoted in full and held as the requirement of record in
[`requirements.md`](requirements.md) row 12. Against it:

- **The exported take is 2:29, so it is inside the 3-minute maximum.** It is above the preferred
  30–90 second band, which the form states as a preference rather than a requirement — the entry
  complies as it stands, and cutting it shorter is an editorial choice, not a defect to fix.
- **YouTube satisfies the host request.** The video is hosted there (link, visibility and how the
  link was verified are in [`video-review-checklist.md`](video-review-checklist.md)).
- **The 2:30–2:50 band below is the self-imposed edit target this file set while the organiser's rule
  was still unread,** not an organiser rule, and it is kept only as the record of how the edit was
  made. The take landed 1–2 s under that band's own floor: the published page's duration fields read
  about 148 s, and only its microformat claims 149 s — that measurement lives in
  [`video-review-checklist.md`](video-review-checklist.md) and nowhere else in this pack.
- If the submitter later chooses to cut to ≤1:30 to sit inside the preferred range, the block order
  below survives shrinking by trimming blocks 2 and 9 first, **never** by cutting the
  blocked-execution beat. Nothing in the entry requires that cut.

## The editing rules that are not negotiable

1. **Cuts are allowed; fabricated responses are not.** Inference took 6.7–47.1 s across the six
   live runs, and 9.6 s on the machine path in the 2026-09-28 QA. Show the producer request
   leaving, cut the dead wait, resume when the real response arrives. A caption like
   `waiting on the model — real` is honest; a sped-up or replayed response is not.
2. **Say the number your stopwatch shows.** Narration says **[read from screen]** wherever a
   duration, confidence or metric appears. Quoting this document's example figures would be
   fabricating an observation.
3. **Never type a secret on camera.** `SENTINEL_INGEST_TOKEN` is exported off-take;
   `scripts/send_demo_event.py` reads it from the environment (`scripts/send_demo_event.py:78`),
   so no token value ever exists in a visible command line or shell history.
4. **No long intro, no company biography, no team roll-call.** The first sentence is the problem.
5. **No silent waits.** Dead air is captioned and cut, never left to run for authenticity.
6. **Terminal setup appears only for the two commands it needs:** the `python scripts/send_demo_event.py --url …`
   invocation and its re-run. Nothing else from the shell.
7. **The label "simulated" is never cropped out** of an action or verification frame. If the crop
   cannot hold both the result and the badge, use the wider shot.

## Blocks

Target speech rate ~140–150 wpm. Narration totals ≈ 350 words ≈ 2:20, which leaves ~30 s of room
for the latency beat and page transitions inside a 2:50 cut.

### 0:00–0:15 — Problem + pitch  *(38 words)*

> Monitoring systems find incidents. Humans re-type them into a chat window. NovaBrain Sentinel
> takes the event directly from the producer, judges it with a live NVIDIA model, and stops
> before touching anything. **Real NVIDIA inference. Safe simulated remediation.**

Screen: console at 1440 px, empty state visible. Lower-third title `NovaBrain Sentinel`.
The bold sentence is the required framing and must be spoken, not just captioned — it is the same
string the console shows as its disclosure badge (`static/index.html:179`).

### 0:15–0:35 — Architecture, and what is real  *(42 words)*

> Here is the whole path. A bearer-guarded endpoint ingests the event. An NVIDIA Nemotron model
> returns a structured assessment: severity, confidence, a recommendation. A policy in plain code
> owns the gate. Actions are simulated. The judgement and the gate are not.

Screen: the single Mermaid diagram from [`architecture.md`](architecture.md), or the loop strip in
the console header (`static/index.html:27-44`) with its real/simulated legend. Hold on the legend
for ~2 s.

### 0:35–0:55 — The machine event arrives  *(42 words)*

> We are not typing. This is the producer's contract: source `novaops`, event type `ram_high`,
> p95 latency from a hundred and eighty milliseconds to two point four seconds. The hint says
> warning. Only a hint. The request goes out.

Screen: terminal, `python scripts/send_demo_event.py --url <demo-url>` typed and executed (demo
scenario step 1). Then `HTTP 201` with the five printed fields (step 3).
EDIT: between "the request goes out" and the next block, cut the wait and caption it
(`waiting on the model — real`). The elapsed time is visible in the cut, so the number stays true.

### 0:55–1:20 — Nemotron's assessment  *(≈55 words)*

> **[read from screen]** seconds later, the answer lands. Severity `high`. Confidence
> **[read from screen]**. `requires_approval: true`. The producer said warning; the model said
> high. On screen: `nvidia/nemotron-3.5-lightning-30b-a3b`, served by NVIDIA Build. Only the
> validated tool arguments reach this page — the model's reasoning text never does.

Screen: panels 1–2, then a zoomed crop on the model-name line (demo scenario steps 4, 6, 7, 8).
NOTE: the hint-vs-verdict contrast is the point of the block. If this take's model agreed with
the hint, keep the footage and re-word to what the screen shows — do not re-run until it
disagrees.

### 1:20–1:45 — The policy, and the blocked execution  *(≈48 words)*

> Now the part that is not a model opinion. High and critical incidents sit behind a human gate,
> and that floor is written in code, not in a prompt. So I press execute before approving.
> Four hundred and nine — approval required. The refusal is written into the audit trail.

Screen: the ⚠ HUMAN APPROVAL REQUIRED state and the `Approval: REAL / Action: SIMULATED` chip, then
the click on *Attempt Execution* (steps 9–10) and the blocked banner, then `execution_blocked`
with actor `operator` and reason `approval_required` (step 11).
NOTE: Chrome will log one red 409 network line. Leave it visible; it is evidence, not a glitch.

### 1:45–2:05 — Approve, then the simulated action  *(≈40 words)*

> I approve as the operator. The allowlist is closed — two actions, both simulated. Scale API
> replicas. There is no orchestrator behind this route, and the console says so instead of
> letting me imply it.

Screen: *Approve* → operator recorded (step 12), then *Execute simulated action* with the
`SIMULATED ACTION` badge in frame (`static/index.html:105`).

### 2:05–2:25 — Verification and the trail  *(≈38 words)*

> Verification reads before and after. Replicas **[read from screen]**, p95 **[read from screen]**,
> error rate **[read from screen]**. And the incident history is one append-ordered trail —
> eight events, including the refusal.

Screen: panel 5 with `VERIFIED` and `Simulation: YES · simulated`, then panel 6 scrolled so the
full 8-event order is legible (steps 13–14). Crop or zoom so event names are readable —
`event_ingested`, `incident_analyzed`, `approval_requested`, `execution_blocked`,
`approval_granted`, `execution_requested`, `execution_finished`, `verification_recorded`.

### 2:25–2:40 — Replay, i.e. idempotency  *(≈22 words)*

> Same event id, same request. **[read from screen]** milliseconds later: duplicate true, same
> incident id. No second model call, no second incident.

Screen: the identical terminal command re-run (step 15) → `HTTP 200`, `duplicate: True`, and the
**same** `incident_id` as block 3. Both outputs should be in one frame or a split crop so the
match is checkable by the judge.

### 2:40–2:50 — Impact and where to look  *(≈22 words)*

> Sentinel is an event-driven operational agent with a hard human gate. Live demo and full source
> are public — links on screen.

Screen: end card. URL text large enough to read at 100 % on a laptop:
`sentinel.novatechsystem.co.uk` and
`github.com/novatechsystemsgroup/novabrain-sentinel`. Hold ≥ 3 s.

## Captions and overlays

- Every number on screen is on-screen text; nothing is asserted only in narration.
- Block 2 and block 7 both need a `SIMULATED` caption visible; the badge is preferable to a
  caption because it is the product's own label.
- Do not add a "AI-generated" or "demo data" watermark — the disclosure badge and the
  `Simulation: YES · simulated` line already do that job, from inside the product.
- Subtitles optional; if added, they must not cover panel 6's event names.

## Re-take rules

| If the take shows… | Then |
|---|---|
| `200` instead of `409` when executing pre-approval | Stop. That is a product defect; report it before filming anything else |
| Severity below `high` (gate never appears) | Re-run once; if it repeats, use fallback incident 1 from `demo-scenario.md` |
| A confidence value different from 0.86–0.87 | Keep it. Narration says **[read from screen]** precisely so this is not a problem |
| The model disagreeing with itself between takes | Fine; the audit trail per incident is what is being shown, not a global claim |
| Any 15 s+ silent wait you decided to keep | Cut it and caption it |
| A token, key, or `.env` contents anywhere in frame | Delete the take, not just the frame |
