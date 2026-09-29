# Video Review Checklist

TASK-016. Use after editing, before upload. Every box must be ticked before the video is marked
done.

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
