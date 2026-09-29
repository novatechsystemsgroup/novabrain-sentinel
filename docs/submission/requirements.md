# Competition Requirements — Verified

TASK-015 §1. Every line below is either quoted from the organiser's public page or marked
`UNKNOWN`. Nothing here is inferred from how hackathons usually work.

**Primary source:** `https://luma.com/claw-agent-challenge-london`, retrieved 2026-09-28
(22:38 UTC). Secondary source: none — the registration form at
`https://airtable.com/appbWMw3ySORLZTgV/pagLOxwVLzgiOaunm/form` renders as an empty shell to an
unauthenticated fetcher, and the organiser states the full details sit behind it: *"After
registering, you'll get access to the full challenge details, submission requirements,
inspiration, and resources."*

**Status vocabulary:** `PASS` = requirement met and evidenced · `PARTIAL` = met in part, with the
gap named · `BLOCKED` = cannot be met from this repository alone · `UNKNOWN` = the rule is not
publicly verifiable, so it is neither claimed nor invented.

| # | Requirement | Source | Status | Evidence | Required action |
|---|---|---|---|---|---|
| 1 | Entry period opens 06:00 PST 2026-09-01 and closes **23:59 PST 2026-10-02** | luma.com, quoted | PASS (time remaining) | Today is 2026-09-28; the deadline is 2026-10-03 06:59 UTC | Submit before the deadline; treat the date as binding on every other task |
| 2 | "Build a long-running claw agent" / "Pick an idea, build a long-running agent around it" | luma.com, quoted | **PARTIAL** | Sentinel is an event-driven agent that runs a full observe→audit loop per event, but "long-running" in its usual sense implies durable state and a life of its own. Sentinel's workflow store and idempotency ledger are per-process memory: a restart clears them (`workflow.py:240`, `ingestion.py:140`). | Do **not** add persistence (§0 freeze). Describe the loop as long-running in the sense of a continuously reachable service that remembers its open incidents while it runs, and state the eviction-on-restart limit in the same sentence. |
| 3 | Open to legal residents of the United Kingdom only, 18+, no corporate or institutional entries | luma.com, quoted | **UNKNOWN** (human fact) | Not verifiable from the repository. Whether the submitter meets UK residency and the individual-entry rule is the submitter's answer, not ours. | Confirm before registering. Flagging this is part of §14, not a code problem. |
| 4 | Employees of sponsors are ineligible | luma.com, quoted | UNKNOWN (human fact) | Same as #3 — a person-level check | Confirm before registering |
| 5 | "A registration equates to a project submission" — one Airtable form | luma.com, quoted | PASS (understood) | Registration *is* the submission: `https://airtable.com/appbWMw3ySORLZTgV/pagLOxwVLzgiOaunm/form` | Fill the form last, after the demo and video exist (§14). Do not register early and assume the entry is in. |
| 6 | Judging covers "technical execution, innovation, and real-world value", among other criteria, at the judges' sole authority, with **no published weights** | luma.com, quoted | PASS (addressed) | Each criterion is mapped to an implementation, an artefact and a demo moment in [`evidence-matrix.md`](evidence-matrix.md) | Nothing further; self-scoring is deliberately absent because the competition does not ask for it |
| 7 | Provided resources include "NVIDIA Build model endpoints and getting-started guides" | luma.com, quoted | PASS | Inference runs against `https://integrate.api.nvidia.com/v1` (`sentinel/nvidia.py:18`) with `nvidia/nemotron-3.5-lightning-30b-a3b` supplied as `NVIDIA_MODEL` (`nvidia.py:97`, `.env.example:16`), through a forced tool call; no other model provider is used | None |
| 8 | Prizes: 1st — GTC Berlin pass, DGX Spark Founders Edition (USD 4,000 value), showcase at NVIDIA Build-a-Claw London; 2nd — GTC Berlin pass, showcase | luma.com, quoted | PASS (informational) | Recorded so the submission copy does not promise anything beyond a placement | None |
| 9 | Winners announced on or around 2026-10-06 | luma.com, quoted | PASS (informational) | Sets the expected wait after submission | None |
| 10 | A public source repository is required (URL, visibility, licence) | **NOT FOUND** publicly; registration-gated | **UNKNOWN** | We ship one anyway: `https://github.com/novatechsystemsgroup/novabrain-sentinel`, PUBLIC, MIT (`LICENSE`), pushed to `main` | Submit the repo URL in the form; do not describe the requirement as if it were published |
| 11 | A live, publicly reachable demo URL is required | NOT FOUND publicly | UNKNOWN | Shipped anyway: `https://sentinel.novatechsystem.co.uk`, verified in §10 QA with `GET /` 200 and `/health` `{"status":"ok","service":"novabrain-sentinel"}` | Include the URL in the form |
| 12 | A demo video is required, of a stated maximum length, hosted at a stated place | NOT FOUND publicly | **UNKNOWN** | Not published, so no length can be quoted as a rule. `video-script.md` therefore targets **2:30–2:50 as a self-imposed edit target**, and says so. | After registering, read the real cap and re-cut only if the target was wrong. Do not present our target as the organiser's rule. |
| 13 | Prescribed submission fields, character limits, or a description template | NOT FOUND publicly | UNKNOWN | `submission-copy.md` is written to word-count ranges chosen for readability, not to a published limit | Transcribe into whatever the form asks for |
| 14 | Screenshots or architecture diagrams must be attached | NOT FOUND publicly | UNKNOWN | `architecture.md` carries one Mermaid diagram; `screenshots.md` plans 6 crops but commits no image binaries | Attach only if the form asks |
| 15 | Mandated model, NIM container, or open-weights requirement | NOT FOUND publicly | UNKNOWN | Sentinel uses a hosted NVIDIA Build endpoint; nothing else is required of us | Record as an open question, not as a passed check |
| 16 | Team-size limit, originality clause, prior-work or third-party-code prohibitions | NOT FOUND publicly | UNKNOWN | Single-maintainer work in this repository only | Read after registration |
| 17 | The page header also lists "14 Oct 2026 13:00 BST" | luma.com, observed | **INCONSISTENT SOURCE** | That date is the London *event* listing; the entry deadline quoted in the rules text is 02 Oct 2026 23:59 PST. Two different things on one page. | **Do not silently pick one.** Submit by 02 Oct 2026 23:59 PST — the earlier of the two — and confirm the distinction once registered. |

## What we deliberately did not do

- No requirement was invented to fill a gap. Seventeen of the lines above come from one page; the
  rest are recorded as `UNKNOWN` with the reason.
- No architecture was changed because of an unverified rule. Requirement #2 ("long-running") is
  the only one where the honest answer is *partial*, and the response is a wording fix, not
  PostgreSQL.
- `nemoclaw.devpost.com` was found during this search and **rejected as a source**: it is a
  different event (NVIDIA × ASUS at UCSC). An older internal note describing this competition as
  an "NVIDIA × Nebius Global AI Hackathon" appears nowhere on the page and is treated as wrong.
- An internal audit dated 2026-09-27 listed "multi-step agentic behaviour", "tool use" and
  "memory" as judging criteria. Those words are **not** on the public page. They are not used as
  requirements anywhere in this pack.
