# Video Review Checklist

TASK-016. **The video exists.** Recorded, exported at **2:29**, uploaded to YouTube as **unlisted**
at <https://youtu.be/bQLiWO1G5Mw>. TASK-018 marks three things DONE and nothing more: recording
complete, upload complete, public share link live.

## Published artefact

| | |
|---|---|
| Title | **NovaBrain Sentinel — NVIDIA Claw Agent Challenge: London Demo** |
| Runtime | **2:29** (the watch page reports `lengthSeconds` 148) |
| Host | YouTube |
| Visibility | **Unlisted** — reached by link, no sign-in required to watch |
| URL | <https://youtu.be/bQLiWO1G5Mw> |

Measured against the published link on 2026-09-29: YouTube's `oEmbed` endpoint answers `200` with
that title and author `NovaTech Systems Group`, and the watch page answers `200` with no
"Sign in to confirm" interstitial — so the id resolves and the page serves the video to a
signed-out visitor. **Unlisted** is the uploader's setting, recorded here rather than inferred: no
file in this repository can read it back.

The 2:29 runtime sits **1 s below** the 2:30–2:50 band `video-script.md` set as a self-imposed edit
target. That band was ours, not the organiser's — the real cap is still `UNKNOWN` behind the
registration form ([`requirements.md`](requirements.md) #12) — so the take stands unless the form
turns out to ask for more.

## How to read the boxes below

This was the checklist for the review pass after editing and before upload. A repository cannot see
a video frame, so TASK-018 does not tick these items from here: the end-to-end watch the operator
attested is recorded in [`checklist.md`](checklist.md) §9, and only the four facts in the table
above are independently measured. An unticked box below is therefore "not re-verified by this
task", never "this check failed".

---

## CONTENT

- [ ] Product name correct: "NovaBrain Sentinel"
- [ ] London challenge wording correct: "NVIDIA Claw Agent Challenge: London"
- [ ] Machine event visible (terminal command, HTTP 201)
- [ ] NVIDIA model name visible: `nvidia/nemotron-3.5-lightning-30b-a3b`
- [ ] Real/simulated split spoken: "Real NVIDIA inference. Safe simulated remediation."
- [ ] Blocked execution visible (409, "Execution blocked by Sentinel policy")
- [ ] Approval visible ("Operator approved")
- [ ] `SIMULATED ACTION` label visible (never cropped out)
- [ ] `VERIFIED` visible with `Simulation: YES`
- [ ] Audit trail visible (8 events in append order)
- [ ] `duplicate: true` replay visible (HTTP 200, same incident id)
- [ ] Demo URL visible: `https://sentinel.novatechsystem.co.uk`
- [ ] Repository URL visible: `https://github.com/novatechsystemsgroup/novabrain-sentinel`
- [ ] LEARN not claimed as implemented

---

## SECURITY

- [ ] No NVIDIA API key (`nvapi-...`) visible
- [ ] No ingest token (`SENTINEL_INGEST_TOKEN` value) visible
- [ ] No `.env` file visible
- [ ] No shell environment dump (`env`, `printenv`, `echo $...`) visible
- [ ] No personal data visible (name, email, phone, address)
- [ ] No private browser tabs visible
- [ ] No passwords visible
- [ ] No hidden provider response (reasoning content, raw model output) visible

---

## CLAIMS

- [ ] No real-remediation claim (everything says "simulated")
- [ ] No production-NovaOps integration claim (it is a "demo emitter" or "compatible producer")
- [ ] No durable-persistence claim (state is in-process, restart clears it)
- [ ] No autonomous high/critical remediation claim (the gate always blocks without approval)
- [ ] No fake timing claim (narration reads numbers from screen, not from a script)

---

## QUALITY

- [ ] Text readable at normal laptop size (100% zoom, not paused at 200%)
- [ ] Audio understandable (no background noise, no distortion)
- [ ] No long silent wait (inference wait is cut and captioned)
- [ ] No accidental notification pop-up visible
- [ ] No mouse wandering (cursor moves with purpose)
- [ ] No terminal typo left visible (or it is cut out)
- [ ] Transitions understandable (browser ↔ terminal ↔ end card)
- [ ] Final URLs readable (held ≥ 3 s, large enough text)

---

## FINAL

- [ ] Watch full export from beginning to end (do not skip sections)
- [ ] Verify duration is within target (2:30–2:50, or the form's cap if different)
- [ ] Verify audio sync (narration matches visuals)
- [ ] Verify uploaded link while signed out / in incognito mode
- [ ] **Only then mark video DONE**
