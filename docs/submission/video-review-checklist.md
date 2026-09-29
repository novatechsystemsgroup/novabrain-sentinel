# Video Review Checklist

TASK-016. **The video exists.** Recorded, exported at **2:29**, uploaded to YouTube as **unlisted**
at <https://youtu.be/bQLiWO1G5Mw>. TASK-018 marks three things DONE and nothing more: recording
complete, upload complete, public share link live.

## Published artefact

| | |
|---|---|
| Title | **NovaBrain Sentinel — NVIDIA Claw Agent Challenge: London Demo** |
| Runtime | **2:29** as the uploader states it. The published page is a second shorter: its `approxDurationMs` values read `147999`, `148021` and `148050` ms, and its two `lengthSeconds` fields disagree with each other — `148` in `videoDetails`, `149` in the microformat — so every read but the microformat's lands on **2:28**. This pack quotes the uploader's figure and names the spread wherever a measurement is claimed. |
| Host | YouTube |
| Visibility | **Unlisted** — reached by link, no sign-in required to watch |
| URL | <https://youtu.be/bQLiWO1G5Mw> |
| Duration rule | **Up to 3 minutes, with 30–90 seconds preferred, on YouTube or Loom** — the official submission form's words, quoted in [`requirements.md`](requirements.md) #12. 2:29 is **inside** the maximum, **above** the preferred range (a preference, not a requirement), and the host is the one the form names. |

Measured against the published link on 2026-09-29: YouTube's `oEmbed` endpoint answers `200` with
that title and author `NovaTech Systems Group`, and the watch page answers `200` with no
"Sign in to confirm" interstitial — so the id resolves and the page serves the video to a
signed-out visitor. **Unlisted** is the uploader's setting, recorded here rather than inferred: no
file in this repository can read it back.

**Measured against the organiser's rule, the runtime complies.** The submission form — opened by the
submitter on 2026-09-29, and quoted in full at [`requirements.md`](requirements.md) #12 — asks for a
demo video **"up to 3 minutes; 30–90 seconds preferred"**, hosted on YouTube or Loom. **2:29 is
inside the 3-minute maximum.** It is above the preferred 30–90 second band; the form calls that a
preference, not a requirement, so the entry needs no re-cut and none is owed — shortening it would be
an editorial choice by the submitter, and `video-script.md` records which blocks such a cut would
take first.

Separately, the same runtime sits **1–2 s below** the floor of the 2:30–2:50 band that
`video-script.md` set for itself *before* that rule was readable (150 s against the 147.999–148.050 s
the page serves, or against the 149 s its microformat claims). That band is ours, not the organiser's,
and the same 1–2 s spread applies to every "how far under the floor" line in this pack. Where a hard
figure matters, use the shorter read — **2:28 — which is inside the maximum by the same margin**.

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
- [ ] Verify duration is inside the organiser's 3-minute maximum (the exported take is 2:29 by the
      uploader's figure and 2:28 by the page's, so both readings clear it; the 2:30–2:50 band in
      `video-script.md` was our own edit target, not the rule)
- [ ] Verify audio sync (narration matches visuals)
- [ ] Verify uploaded link while signed out / in incognito mode
- [ ] **Only then mark video DONE**
