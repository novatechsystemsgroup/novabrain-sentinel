# ADR-0003: Machine Event Ingestion with a Bearer Guard and an In-Process Idempotency Ledger

## Status

Accepted

## Date

2026-09-28

## Context

Through TASK-012/TASK-013 Sentinel could analyse an incident an **operator** typed into the
console. That inverts the loop the product claims to close: a real operational agent is
*observed* by its environment, and events arrive from monitoring processes faster than a person
can retype them. Until an upstream service can post an event, OBSERVE is a manual step and the
demo story starts with the wrong actor.

Adding a machine front door raises four decisions at once, each with a version that would be
wrong for this slice:

1. **What is the contract?** The obvious move is to accept whatever an alerting service already
   sends, or to design a full event taxonomy for it. Neither is available: the reference
   monitoring codebase (NovaOps) has no machine-readable outbound event at all — its
   `TriggerAlert(...)` feeds pre-rendered text/HTML into a Telegram `http.Post` and
   `smtp.SendMail`. There is no producer to conform to, only a shape to invite.
2. **Does a machine get a second workflow?** Two paths through `analyze → approve → execute`
   would drift: the audit trail, the approval floor and the console would each have to be
   duplicated and kept in agreement by hand.
3. **What does an expensive endpoint do when a producer retries?** One live analysis is 13–48 s
   of paid inference. A producer that times out at 30 s and retries is billed twice and creates
   two incidents for one event, which then shows two contradictory audit trails for one outage.
4. **Who may call it?** The route costs money and changes state. The existing surface is
   deliberately public; a machine route can be, but only if the documentation does not then
   claim protection it did not install.

## Decision

Add **one authenticated route, one optional audit event, and one bounded in-process ledger**,
and leave every existing leg untouched:

- `POST /api/v1/events/ingest` accepts `OperationalEvent` — `event_id` (required, producer-stable,
  the idempotency key), `source`, `event_type`, `title`, `description`, `severity_hint`,
  `evidence`, and an optional timezone-aware `observed_at`. No monitoring-specific fields the
  current slice would not use.
- `sentinel/ingestion.py` is the whole new surface area: `require_ingest_token()` (a FastAPI
  dependency comparing `SENTINEL_INGEST_TOKEN` with `hmac.compare_digest`) and `IdempotencyLedger`
  (a `dict` of ≤ 200 `event_id → incident_id` entries behind one lock).
- The event is **normalised into the existing `IncidentEvent`** and handed to the existing
  `analyze_event()` and `WorkflowStore.record_analysis()`. There is no ingestion-specific
  provider code, no ingestion prompt variant, and no second state machine. `analysis.py` and
  `nvidia.py` are not modified.
- Ingestion contributes one extra audit event, `event_ingested` (actor `sentinel`, details
  `{event_id, source, event_type, observed_at, received_at}`), appended **before**
  `incident_analyzed` and only when the request came through the machine door.
- The response is a pointer — `{event_id, incident_id, workflow_state, duplicate, console_path}`
  with a **relative** `/?incident=<id>` path — and the console gains query-parameter routing into
  the panels it already had.
- Processing is **synchronous**: the producer's request is held for the whole inference. No queue,
  no worker, no callback URL.
- Idempotency is per-process memory. A restart clears it, and that is documented rather than
  worked around with infrastructure.

Machine-to-machine ingestion is bearer-token protected. The public hackathon console remains
intentionally unauthenticated — and so does `POST /api/v1/incidents/analyze`, which can still
trigger paid inference. The guard is one route wide, and the docs say so in exactly those terms.

## Rationale

1. **Reuse over parallel paths.** The approval gate, the audit trail and the console are the
   interesting parts of this product. Routing machines into the same workflow means a fix to the
   gate is a fix for both doors, and it keeps `WorkflowStore` the single state-transition
   authority. A second workflow would have been the most convenient thing to write and the first
   thing to contradict the original.

2. **`event_id` alone is the dedup key.** Keying on a content hash would make a producer's retry
   of an *edited* event a new incident, and would give Sentinel an opinion about what counts as
   "the same outage". The producer owns stability; Sentinel owns idempotency for the id it was
   given. One field, one guarantee.

3. **A pre-flight claim, not a post-hoc check.** `ledger.reserve()` runs before the model is
   called, so a concurrent duplicate answers `409 event_in_progress` instead of racing into two
   paid analyses. Claims are never evicted, and a provider failure releases the claim so the
   producer can retry — a guard that leaks reservations on error is a guard that eventually
   refuses the event it exists to protect.

4. **An explicit `503 ingest_ledger_full` beats silent loss.** At capacity the ledger evicts only
   finished entries; if everything tracked is in flight, the request is refused. This mirrors
   `503 workflow_store_full` for the same reason: an idempotency guard that discards an in-flight
   event to accept a new one has traded a 503 for a duplicate inference and a split audit trail.

5. **In-process is the honest scope line — and it is stated twice.** Redis or a small table would
   make idempotency survive a restart. This slice does not need that; it needs the demo not to
   double-charge itself when a producer retries, which a `dict` provides. The durability limit is
   documented in the README, the architecture doc, the error message and the deployment guide, and
   the ledger is a class with an interface so the day storage arrives is a swap, not a rewrite.

6. **The token guards the door that needed guarding.** One secret, one route, constant-time
   comparison, no sessions/JWT/users, and the browser console left alone — a hackathon judge who
   cannot log in is a judge who does not see the product. The alternative (global auth middleware)
   would have contradicted the deliberately public demo surface for no gain in the thing under
   review.

7. **Synchronous is acceptable because the event rate is low.** A monitoring service flagging an
   offline VPS produces tens of events per day, not thousands per second. Holding one HTTP request
   for tens of seconds is a real limit that is documented, versus a queue that would add a moving
   part and hide the latency the demo is trying to show.

8. **Producer vocabulary is normalised at the edge only.** `warning → medium` and the open
   `event_type` pattern keep the machine contract compatible without leaking producer words into
   Sentinel's own classification. The NVIDIA assessment still decides severity; the alias only
   stops a legitimate event from being rejected as invalid input.

9. **Relative `console_path` keeps the deployment irrelevant.** The service does not know its
   public hostname, and a hardcoded one breaks behind every domain, preview and port mapping.
   Returning `/…` lets the producer decide how to render a link.

## Consequences

- **Positive:**
  - The demo now starts with a producer posting an event, so "the operator no longer creates the
    incident manually" is literally what happens, end to end, against a live model.
  - Every existing safety property holds for machine events without duplication: the pre-approval
    `409` blocks execution identically, and the trail simply starts one event earlier.
  - A retrying producer costs one inference, not several, and gets the same `incident_id` back.
  - The `/analyze` contract is byte-compatible; nothing that worked before this change behaves
    differently.
  - The new code is two focused concerns in one small module, independently testable — the ledger
    has no HTTP or provider dependency at all.

- **Negative:**
  - **A restart clears idempotency memory** (and the workflow store with it). Replaying an event
    after a redeploy produces a new incident. Documented, not fixed.
  - One shared bearer secret, no rotation or revocation story: changing it means redeploying, and
    every producer holds the same credential.
  - Two authenticated-by-different-means doors on one product. The machine route needs a header;
    the human route needs nothing. That asymmetry must be kept accurate in every document.
  - Synchronous ingestion means a slow provider holds a connection. It is not a high-throughput
    webhook receiver, and event volume is bounded by the single worker.
  - `event_type` values are carried, not interpreted: Sentinel will happily ingest
    `database_on_fire`, and the console will show it. The bound is shape, not meaning.

- **Risks:**
  - A contributor adds a Redis- or DB-backed idempotency layer without a second look at the
    eviction and release semantics — the failure mode to preserve is "never drop an in-flight
    claim, always release on error", which is what the tests pin.
  - Documentation drift toward overstating the guard. The tests assert against specific forbidden
    claims (e.g. that the API "is authenticated" or that protection is global) so an overstatement
    fails CI rather than shipping.
  - Anyone with a valid `/?incident=<id>` link can act on that incident, because the console is
    unauthenticated by design. Acceptable for the demo; must be reconsidered before this surface
    is used operationally.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Reuse a NovaOps outbound event as the producer | NovaOps has no machine-readable outbound event — its transports are Telegram `http.Post` and `smtp.SendMail` fed pre-rendered text. Claiming an integration would be false; the emitter is honestly labelled a stand-in. |
| A monitoring-specific event taxonomy with an enum of alert types | Freezes a vocabulary belonging to a producer that does not exist yet, and rejects future events at the door. Replaced by a bounded identifier pattern plus free pass-through. |
| A parallel ingestion workflow (own store, own audit, own gate) | Two sources of truth for one incident, duplicated policy, and a drift surface in the most safety-critical part of the product. |
| Redis / database-backed idempotency | Adds infrastructure to buy durability the slice does not need, and hides the restart-clears-memory limit the docs are required to state. The ledger class keeps the interface so the swap stays local. |
| Dedup on a hash of event content | Makes an edited retry a new incident and has Sentinel define "the same event". The producer owns stability via `event_id`. |
| Silent eviction of the oldest ledger entry at capacity | Discarding an in-flight claim admits a duplicate paid inference and a second trail for one outage. Replaced by finished-only eviction plus `503 ingest_ledger_full`. |
| Async ingestion (queue, Celery, background task, callback URL) | A second moving part that hides the latency the demo is about, plus a callback surface to secure, for an event rate that does not need it. |
| Global auth middleware over every endpoint | Would break the deliberately public one-click console for no gain in what is being evaluated, and is a platform concern (domain/Traefik/allowlist) rather than an application one. |
| Absolute `console_path` from a configured base URL | Couples the API response to deployment topology and breaks previews; a relative path works everywhere and is the honest answer for a service that does not know its hostname. |
| Accepting naive `observed_at` timestamps | Two producers, two different assumptions about the clock, one silently shifted audit trail. Aware-only input, normalised to UTC. |
