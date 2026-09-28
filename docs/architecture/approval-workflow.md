# Approval Workflow

The DECIDE → ACT → VERIFY leg: an assessed incident becomes a stateful record an operator
approves or rejects, and an approved incident "executes" a remediation that is simulated.

> **What is real here:** the assessment comes from a real NVIDIA model call
> ([incident-analysis.md](incident-analysis.md)).
> **What is simulated:** the action, its metrics, and the verification. Sentinel never
> restarts a service, never scales a deployment, and no workflow code contacts an
> orchestrator, a host, or any network endpoint — the only outbound call in the whole
> codebase is the NVIDIA inference request in `nvidia.py`, which is upstream of this leg.
> `restart_api_service` is a dict lookup that returns authored numbers.
> This is real NVIDIA inference + simulated execution and verification — **not real
> remediation**.

```
POST /api/v1/incidents/analyze  (real model call, then the record is filed)
    │
    ├─ requires_approval true ──→ awaiting_approval ──approve──→ approved ─┐
    │                                    │                                 │
    │                                 reject                                │ execute
    │                                    ▼                                 ▼
    └─ requires_approval false ─→ analyzed ──── execute ────→        executing
      (no approval needed)                                          │        │
                                                       verified ◄───┘        └───► failed
```

`rejected`, `verified` and `failed` are terminal — they have no outgoing transition. Every
other arrow is taken inside one lock, and every state change appends an audit event.

## Modules

| File | Responsibility | Depends on |
|---|---|---|
| `sentinel/schemas.py` | `WorkflowState`, `ActionName`, `DecisionRequest`, `ExecuteRequest`, `AuditEvent`, `ApprovalDecision`, `Verification`, `IncidentWorkflow` | pydantic |
| `sentinel/simulation.py` | the action catalog and the metric snapshots it returns | `schemas` |
| `sentinel/workflow.py` | the state machine, the approval gate, the audit trail, the in-memory store | `schemas`, `simulation` |
| `sentinel/api.py` | routes and workflow-error → HTTP-status mapping | `workflow`, FastAPI |

`analysis.py` and `nvidia.py` are **not** part of this leg and were not modified by it. The
store only ever receives an `IncidentAnalysis` that the analysis path already returned, so a
workflow bug cannot change what the model reported — and `POST /analyze` still answers with
the identical `IncidentAnalysis` body it answered with before this feature existed. The
workflow view is a separate resource read from a separate endpoint.

## States

| State | Meaning | Reachable from |
|---|---|---|
| `analyzed` | assessment filed; no operator decision needed | initial (when `requires_approval` is false) |
| `awaiting_approval` | assessment filed; an operator must decide | initial (when `requires_approval` is true) |
| `approved` | an operator said yes | `awaiting_approval` |
| `rejected` | an operator said no | `awaiting_approval` |
| `executing` | an action is being applied | `analyzed`, `approved` |
| `verified` | simulated action reported recovery | `executing` |
| `failed` | simulated action reported no recovery | `executing` |

`executing` exists so the machine is honest about having an in-flight step, but it is
**transient and never observed over HTTP**: the simulation runs inside the same critical
section as the transition into and out of it. A request either has not started the action or
has already recorded its outcome, so no incident can be stranded in `executing` by a failure
halfway through.

`verified`, `failed` and `rejected` are terminal — they have no outgoing transition. A
rejection in particular cannot be reversed by approving afterwards; `POST /approve` on a
rejected incident is `409 invalid_transition` ("Cannot approve an incident in state
'rejected'."). The permanence comes from the machine having no edge, not from a runtime
comparison that could be forgotten.

## The execution invariant

Execution is allowed **iff** `assessment.requires_approval == false` **or**
`workflow.state == "approved"`. "An approval decision exists" is not the rule — a `rejected`
record also carries an approval decision, and it must never execute.

`workflow.execution_block_reason()` evaluates the guards in this order and is the single
source of truth (14 cases pinned in `tests/test_workflow.py`):

| `state` | `requires_approval: false` | `requires_approval: true` |
|---|---|---|
| `analyzed` | **execute** | blocked `approval_required` |
| `awaiting_approval` | n/a¹ | blocked `approval_required` |
| `approved` | **execute** | **execute** |
| `rejected` | blocked `approval_rejected` | blocked `approval_rejected` |
| `executing` | blocked `already_executed` | blocked `already_executed` |
| `verified` | blocked `already_executed` | blocked `already_executed` |
| `failed` | blocked `already_executed` | blocked `already_executed` |

¹ Unreachable: the initial state is *derived* from `requires_approval` when the record is
filed, so an incident that needs approval starts in `awaiting_approval` and one that does not
starts in `analyzed`.

Two consequences worth stating plainly:

- A `low` or `medium` incident the model did not flag is **executable the moment it is
  analysed** — no operator round-trip. This is the `requires_approval == false` half of the
  invariant, not an oversight.
- Such an incident also **cannot be vetoed**, because `reject` is only legal from
  `awaiting_approval`. To withdraw permission for an already-analysed low incident you fix the
  policy, not the record. The TASK-011 approval floor closes the dangerous half of this gap:
  `high` and `critical` incidents always require approval regardless of what the model said.

No high or critical incident ever executes autonomously.

## Simulated execution

`simulation.py` is the only code in the repository that "does" anything, and it does nothing
to a system. Each catalog entry carries `executes: Literal[False] = False` and
`simulated: Literal[True] = True`, and a test asserts both for every entry, so adding a real
side effect means editing that contract deliberately.

| Action | Modelled effect | Recovers |
|---|---|---|
| `scale_api_replicas` | replicas 2 → 4, p95 2400 → 610ms, error rate 8.2 → 0.4% | every severity |
| `restart_api_service` | one restart, p95 2400 → 540ms, error rate 8.2 → 0.6% | `low`, `medium`, `high` — **not** `critical` |

`restart_api_service` on a `critical` incident therefore produces
`{"status": "failed", "success": false, ...}` with `after` identical to `before`. That is the
deterministic route to `failed`, chosen instead of a random failure rate: the same action on
the same severity always gives the same verification, so the demo and the tests are
reproducible, and both terminal states are reachable on purpose.

Verification results are `{"status", "simulated": true, "before", "after", "success"}` — the
metrics are authored constants, not measurements. `ActionName` is a `Literal`, so an unknown
action is a pydantic `422` before the store is touched at all; the incident's state is
unchanged and nothing is audited. The catalog is advertised in OpenAPI as an enum, so a UI
renders the permitted actions from the schema rather than a hardcoded list.

## Audit trail

Every transition appends `{"timestamp", "event", "actor", "details"}` to the incident's
`audit_trail`, where `actor` is `sentinel` or `operator`.

| Event | Actor | Written when |
|---|---|---|
| `incident_analyzed` | sentinel | analysis filed |
| `approval_requested` | sentinel | analysis filed and approval is required |
| `approval_granted` / `approval_rejected` | operator | a decision is accepted |
| `execution_requested` | operator | an allowed execution starts (`mode: "simulated"`) |
| `execution_blocked` | operator | an execution attempt is refused |
| `execution_finished` | sentinel | the simulation returns, with the resulting state |
| `verification_recorded` | sentinel | the verification is stored |

**Append order is the authoritative sequence.** `execution_finished` and
`verification_recorded` are 4 µs apart in the run below because each takes its own
`utc_now()` reading — but nothing guarantees that gap. Two calls made inside one critical
section can land on the same value once the clock's resolution is coarser than the work
between them, so consumers must not sort or de-duplicate by timestamp, and tests assert the
event *order* plus *non-decreasing* (not strictly increasing) timestamps. Stamps are ISO-8601
UTC with microseconds, which keeps them fixed-width and usually sortable.

Refusals are evidence. A blocked attempt is audited *before* the error is raised, so the trail
shows the attempted action and the reason code:

```
2026-09-28T18:49:55.710578+00:00  incident_analyzed      sentinel  {"severity":"high","confidence":0.92,"requires_approval":true,…}
2026-09-28T18:49:55.710785+00:00  approval_requested     sentinel  {"severity":"high","reason":"Sentinel approval policy requires an operator decision."}
2026-09-28T18:49:55.731204+00:00  execution_blocked      operator  {"action":"scale_api_replicas","reason":"approval_required"}
2026-09-28T18:49:55.734057+00:00  approval_granted       operator  {"note":"Approved for simulated scale-out on the demo cluster."}
2026-09-28T18:49:55.735724+00:00  execution_requested    operator  {"action":"scale_api_replicas","mode":"simulated","note":"simulated only"}
2026-09-28T18:49:55.735797+00:00  execution_finished     sentinel  {"action":"scale_api_replicas","state":"verified"}
2026-09-28T18:49:55.735801+00:00  verification_recorded  sentinel  {"status":"verified","success":true,"simulated":true}
2026-09-28T18:49:55.737154+00:00  execution_blocked      operator  {"action":"restart_api_service","reason":"already_executed"}
```

This is the real trail from a live run: one genuine NVIDIA analysis, one premature execution
attempt, one approval, one simulated action, one repeat attempt. A request that is rejected
for a bad *body* (422) never reaches the store, so it leaves no trace — the trail records
attempts against a known incident, not malformed traffic.

## Store semantics

`WorkflowStore` is a `dict` guarded by an `RLock`, living in the process.

- **No database.** This is deliberate for this slice: PostgreSQL remains out of scope so the
  loop can be demonstrated end to end first.
- **Single process, single replica.** State is per-process, so running more than one
  container (or restarting one) splits or erases the picture: an incident approved on one
  worker is unknown to another, and `POST /execute` on a restarted instance is a 404. See
  [`docs/deployment/coolify.md`](../deployment/coolify.md) for the deployment consequence.
- **Capacity is a leak guard, not a feature.** `MAX_TRACKED_INCIDENTS = 200`. When the store
  is full, `_make_room()` evicts the *oldest finished* incident — only `verified`, `failed`
  and `rejected` are eligible. `analyzed`, `awaiting_approval`, `approved` and `executing` are
  **never** evicted; the protected set is derived from the declared states minus the terminal
  ones and pinned by an import-time assert, so adding a state to `WorkflowState` cannot
  silently land it on the evictable side.
- **Full and nothing finished is an error, not a deletion.** If every tracked incident is
  active, `POST /analyze` fails with `503 workflow_store_full` rather than discarding live
  work. The message says so: *"Active incidents are never evicted; this slice keeps state in
  memory, so a restart is the reset."*
- **Reads return deep copies.** Routes get `model_copy(deep=True)`, so a handler cannot mutate
  shared state by accident.
- **No authentication, no authorisation.** Every actor is recorded as `operator` because
  anyone who can reach the port is one. This is a knowingly-unauthenticated demo slice; 403 is
  left unclaimed so a real auth layer can occupy it later.

## Failure modes

| Condition | HTTP | `detail.error` |
|---|---|---|
| Unknown incident id on any workflow route | 404 | `incident_not_found` |
| Execution attempted before approval | 409 | `approval_required` |
| Execution attempted after rejection | 409 | `approval_rejected` |
| Execution attempted twice | 409 | `already_executed` |
| Approve/reject outside `awaiting_approval` | 409 | `invalid_transition` |
| Unknown action | 422 | pydantic detail |
| Store full of active incidents | 503 | `workflow_store_full` |

Errors use the same envelope as the analysis path
(`{"detail": {"error": "<code>", "message": "<safe text>"}}`), and 409 is reserved for state
conflicts so it stays distinct from a future permission failure.

## API surface

| Method | Path | Body | Returns |
|---|---|---|---|
| `POST` | `/api/v1/incidents/analyze` | `IncidentEvent` | `IncidentAnalysis` (unchanged) |
| `GET` | `/api/v1/incidents/{incident_id}` | — | `IncidentWorkflow` |
| `POST` | `/api/v1/incidents/{incident_id}/approve` | `{"note"?}` optional | `IncidentWorkflow` |
| `POST` | `/api/v1/incidents/{incident_id}/reject` | `{"note"?}` optional | `IncidentWorkflow` |
| `POST` | `/api/v1/incidents/{incident_id}/execute` | `{"action", "note"?}` | `IncidentWorkflow` |

`GET /api/v1/incidents/{incident_id}` is the whole evidence bundle: the original
`IncidentEvent`, the full NVIDIA `analysis`, the current `state`, the `approval` decision with
its note and timestamp, the selected `action`, the `verification` result, and the ordered
`audit_trail`.

## Testing

`tests/test_workflow.py` drives one app instance — and therefore one store — through several
requests over `httpx.ASGITransport`, with `httpx.MockTransport` standing in for NVIDIA Build.
It covers the approval requirement, execution blocked before approval, approval enabling
execution, rejection blocking it permanently, the full invariant truth table, audit ordering
and timestamp monotonicity, the required shape of every event, determinism of both the
`verified` and `failed` paths, the catalog guard, the 422-before-transition case, terminal-only
eviction, the `503` when nothing is finished, and that workflow responses leak neither
`reasoning_content` nor the provider key. The pre-existing 27 analysis and smoke tests are
unmodified, which is what "existing NVIDIA analysis remains unchanged" means in practice.
