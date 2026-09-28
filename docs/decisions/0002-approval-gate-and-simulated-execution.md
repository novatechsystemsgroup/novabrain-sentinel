# ADR-0002: Approval Gate with In-Memory State and Simulated Execution

## Status

Accepted

## Date

2026-09-28

## Context

Through TASK-011 Sentinel could analyse an incident: an event in, a validated NVIDIA
assessment out. That is a read-only capability — it produces a recommendation nobody can act
on, and it leaves the core loop unfinished at its most important edge (DECIDE → ACT → VERIFY).

Turning analysis into a workflow raises three decisions at once, and each has a version that
would be wrong for a competition slice:

1. **Who is allowed to act?** An agent that remediates on its own is the pitch and the hazard.
   For `high` and `critical` incidents, autonomy is exactly what an operator is paying Sentinel
   to remove.
2. **Where does workflow state live?** The wider Sentinel architecture eventually wants
   durable incident and audit records, but adding storage to this slice turns a one-day build
   into a migration, a connection pool and a second moving part in front of a demo — and
   `requirements.txt` today carries only the HTTP/pydantic stack.
3. **What does "execute" touch?** The loop only looks complete once an action runs — and
   running a real action from an unauthenticated, single-replica, hackathon service is not
   defensible.

## Decision

Implement the workflow as a **single-process state machine with a mandatory human gate and a
simulated acting hand**:

- `sentinel/workflow.py` owns every state transition. Analysis stays as it was; the store only
  receives analyses that were already returned.
- States are `analyzed`, `awaiting_approval`, `approved`, `rejected`, `executing`, `verified`,
  `failed`. `verified`, `failed` and `rejected` are terminal.
- Execution is permitted **iff** `assessment.requires_approval == false` **or**
  `workflow.state == "approved"`. This is one pure predicate
  (`execution_block_reason()`), pinned by a truth table in tests.
- Every transition — including every *refused* attempt — appends an audit event carrying
  `{timestamp, event, actor, details}`. Append order, not timestamp order, is authoritative.
- State lives in a bounded in-process dict. Only finished incidents may be evicted; when the
  store is full of live incidents the API answers `503 workflow_store_full` instead of
  discarding work.
- Actions come from a closed catalog (`scale_api_replicas`, `restart_api_service`) typed as a
  `Literal`, and each entry declares `executes: Literal[False]`. Executing means returning
  authored metric snapshots, deterministically.

No new environment variables, no new dependencies, no database.

## Rationale

1. **The gate is the product.** A judge evaluating an "operational AI agent" is really asking
   whether they would trust it. Trustworthiness here is the *refusal*: `POST /execute` before
   approval fails with 409 and lands in the audit trail. That behaviour is worth more than any
   additional capability bolted on beside it.

2. **One predicate, not two policies.** The approval floor (`high`/`critical` always need
   approval, from TASK-011) and the execution gate consult the same `requires_approval` field
   the analysis leg already wrote. A second, independent "is this dangerous?" check would
   eventually disagree with the first — and the disagreement would be silent.

3. **Refusals are evidence.** Auditing blocked attempts makes the trail a record of what was
   *asked*, not only of what happened. It also means the safety property is demoable without
   instrumenting the test suite: the trail itself shows the attempt and the reason code.

4. **Permanence by absence of edges.** A rejected incident cannot later be approved because the
   state machine has no such transition — not because a runtime comparison happens to catch it.
   Rules that are structurally impossible outlive refactors.

5. **In-memory is an honest scope line.** PostgreSQL is on the roadmap; introducing it now
   would buy durability the slice does not need yet, while adding a failure mode that hides the
   thing under review. The limit is declared in the docs and in the error message rather than
   papered over.

6. **Simulation keeps the demo safe and reproducible.** Fixed inputs give fixed outputs, so
   both terminal states are reachable on purpose (`restart_api_service` never recovers a
   `critical` incident) without a random failure generator or dead code.

7. **The catalog is the whole blast radius.** `ActionName` is a `Literal`, so an unknown action
   is a 422 before the store is touched, and `executes: Literal[False]` on every entry makes
   "nothing real happens" a greppable, test-asserted contract rather than a comment.

## Consequences

- **Positive:**
  - The full loop — observe, understand, decide, act, verify — is demonstrable in one HTTP
    session against a real model.
  - `POST /api/v1/incidents/analyze` responses are byte-identical to TASK-011; the workflow is
    purely additive.
  - The safety properties are covered by 46 tests that need no provider and no infrastructure.
  - Swapping the in-memory store for a database later touches `workflow.py` only, because it is
    the sole module that mutates state.

- **Negative:**
  - Workflow state dies with the process. A restart clears the audit trail, so evidence must be
    captured out-of-band during a demo (or the deployment must be single-replica and stable).
  - Exactly one replica may serve traffic: an incident approved on one worker is a 404 on
    another. This is now a documented deployment constraint, enforced by convention only.
  - Nothing verifies a *real* recovery. The `before`/`after` metrics are authored constants,
    which must be labelled as such in every evaluation artifact.
  - No authentication: any reachable client can approve its own incident. Every actor is
    recorded as `operator` because there is nothing else to record.
  - `verified` and `failed` are terminal by design, so a mistyped action cannot be retried — the
    incident must be re-analysed under a new id.

- **Risks:**
  - A future contributor may treat `simulation.py` as scaffolding and wire a real client into
    it. The catalog contract and its test are the guard; they should be read before extending.
  - The eviction ceiling (200 active incidents) is generous for a demo but unbounded in time: a
    long-lived process accumulating unclosed incidents will eventually return 503. Closing
    incidents is the operator's responsibility, and the error message says so.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Autonomous execution for `high`/`critical` | The inverse of the point. Unreviewed remediation from an unauthenticated endpoint is the failure mode the gate exists to prevent. |
| Persist workflow state and audits in PostgreSQL | A migration, a pool and a second failure mode for durability this slice does not need; deferred to the storage task with the store interface already isolated. |
| Real remediation (kubectl / systemd / NovaOps hooks) | Cannot be safely exercised in a competition demo, and would make tests destructive. Simulated actions plus a closed catalog keep the loop demonstrable and the host untouched. |
| Emit `execution_blocked` only, without recording it | Loses the most persuasive evidence in the trail: the moment somebody tried to act early. |
| Randomly fail simulations | Non-reproducible tests and demos. Deterministic severity-dependent outcomes reach both terminal states on purpose. |
| Silent FIFO eviction at capacity | Would delete live workflows and their audits — the opposite of an accountability feature. Replaced by terminal-only eviction and an explicit 503. |
| An agent framework (LangGraph / AutoGen) for the loop | Imports a dependency graph to express five states and one invariant that are clearer as a lock and a predicate. |
| Timestamp-ordered audit trail | Adjacent events legitimately share a microsecond stamp; making order depend on the clock would put the trail's correctness at the mercy of resolution. |
