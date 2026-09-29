# Narration Cheat Sheet

TASK-016. One page. Read these during recording. Where it says **[READ FROM SCREEN]**, read the
actual value from the screen — never quote a fixed number from this document.

---

## INTRO

Monitoring systems find incidents. NovaBrain Sentinel receives those events directly and turns them
into an operational decision workflow.

Real NVIDIA inference. Safe simulated remediation.

---

## MACHINE EVENT

We are not typing. This is a machine event from a monitoring producer. The request goes out.

---

## NVIDIA ASSESSMENT

**[READ FROM SCREEN]** seconds later, the answer lands.

Severity **[READ FROM SCREEN]**. Confidence **[READ FROM SCREEN]**. Model:
**[READ FROM SCREEN]**.

The producer's hint was only a hint. The model made the call.

---

## SAFETY GATE

Now the part that is not a model opinion. High and critical incidents sit behind a human gate,
and that floor is written in code, not in a prompt.

So I press execute before approving.

Execution blocked by Sentinel policy. The refusal is written into the audit trail.

---

## APPROVAL + ACTION

I approve as the operator.

The allowlist is closed. Both actions are simulated. There is no orchestrator behind this route,
and the console says so instead of letting me imply it.

---

## VERIFY + AUDIT

Verification reads before and after.

Replicas **[READ FROM SCREEN]**. P95 latency **[READ FROM SCREEN]**. Error rate
**[READ FROM SCREEN]**.

And the incident history is one append-ordered trail — eight events, including the refusal.

---

## IDEMPOTENCY

Same event id, same request. **[READ FROM SCREEN]** milliseconds later: duplicate true, same
incident id. No second model call, no second incident.

---

## CLOSE

NovaBrain Sentinel — an event-driven operational agent with a hard human gate.

Live demo and full source are public. Links on screen.
