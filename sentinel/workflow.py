"""In-memory incident workflow: approval gate, audit trail, simulated execution.

This is the only module that may change an incident's state. The analysis leg
(``analysis.py`` / ``nvidia.py``) is untouched by it, so a workflow bug can never
alter what the model reported.
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Literal

from . import simulation
from .schemas import (
    ActionName,
    ApprovalDecision,
    AuditEvent,
    IncidentAnalysis,
    IncidentEvent,
    IncidentWorkflow,
    WorkflowState,
)

MAX_TRACKED_INCIDENTS = 200

# Only a finished incident may leave the store. Deriving the protected set from
# the declared states means adding a state to the Literal cannot silently land on
# the evictable side of this rule.
TERMINAL_STATES = frozenset({"verified", "failed", "rejected"})
NON_EVICTABLE_STATES = frozenset(set(WorkflowState.__args__) - TERMINAL_STATES)
assert NON_EVICTABLE_STATES == frozenset(
    {"analyzed", "awaiting_approval", "approved", "executing"}
), "every workflow state must be either terminal or protected from eviction"

WORKFLOW_ERROR_STATUS = {
    "incident_not_found": 404,
    "approval_required": 409,
    "approval_rejected": 409,
    "already_executed": 409,
    "invalid_transition": 409,
    "workflow_store_full": 503,
}

BLOCKED_MESSAGE = {
    "approval_required": "This incident is awaiting an operator approval.",
    "approval_rejected": "This incident was rejected. A rejection is permanent.",
    "already_executed": "This incident has already been executed.",
}

# The decision is stored as its past tense ("approved") but a refusal has to read
# as the operator's own verb, and the state belongs in the sentence.
DECISION_EVENT = {"approved": "approval_granted", "rejected": "approval_rejected"}
DECISION_VERB = {"approved": "approve", "rejected": "reject"}

logger = logging.getLogger("sentinel.workflow")


class WorkflowError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def execution_block_reason(requires_approval: bool, state: WorkflowState) -> str | None:
    """None when execution is permitted, otherwise the reason code.

    Guards are ordered: a finished or in-flight incident is closed regardless of
    what its assessment said, a rejection outlives every other consideration,
    and only then does the approval invariant apply.
    """
    if state in ("executing", "verified", "failed"):
        return "already_executed"
    if state == "rejected":
        return "approval_rejected"
    if not (requires_approval is False or state == "approved"):
        return "approval_required"
    return None


class WorkflowStore:
    """Bounded, per-process store of incident workflow records.

    Records are dicts keyed by incident id, so insertion order is stable and
    eviction takes the oldest finished incident. Capacity is a leak guard, not a
    feature: an incident nobody closes will eventually push out the oldest
    finished one, and when even that is impossible the store fails loudly
    instead of deleting live work.
    """

    def __init__(self, capacity: int = MAX_TRACKED_INCIDENTS):
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self.capacity = capacity
        self._records: dict[str, IncidentWorkflow] = {}
        self._lock = threading.RLock()

    # -- reads ---------------------------------------------------------------

    def get(self, incident_id: str) -> IncidentWorkflow:
        with self._lock:
            return self._copy(self._require(incident_id))

    # -- writes --------------------------------------------------------------

    def record_analysis(self, event: IncidentEvent, analysis: IncidentAnalysis) -> IncidentWorkflow:
        assessment = analysis.assessment
        state: WorkflowState = "awaiting_approval" if assessment.requires_approval else "analyzed"
        with self._lock:
            self._make_room()
            record = IncidentWorkflow(
                incident_id=analysis.incident_id,
                state=state,
                updated_at=utc_now(),
                event=event,
                analysis=analysis,
            )
            self._audit(
                record,
                "incident_analyzed",
                "sentinel",
                {
                    "severity": assessment.severity,
                    "confidence": assessment.confidence,
                    "requires_approval": assessment.requires_approval,
                    "model": analysis.model.model,
                },
            )
            if assessment.requires_approval:
                self._audit(
                    record,
                    "approval_requested",
                    "sentinel",
                    {
                        "severity": assessment.severity,
                        "reason": "Sentinel approval policy requires an operator decision.",
                    },
                )
            self._records[analysis.incident_id] = record
            return self._copy(record)

    def decide(
        self, incident_id: str, decision: Literal["approved", "rejected"], note: str | None = None
    ) -> IncidentWorkflow:
        with self._lock:
            record = self._require(incident_id)
            if record.state != "awaiting_approval":
                raise WorkflowError(
                    "invalid_transition",
                    f"Cannot {DECISION_VERB[decision]} an incident in state '{record.state}'.",
                )
            record.state = decision
            record.approval = ApprovalDecision(decision=decision, note=note, decided_at=utc_now())
            self._audit(record, DECISION_EVENT[decision], "operator", {"note": note} if note else {})
            return self._copy(record)

    def execute(
        self, incident_id: str, action: ActionName, note: str | None = None
    ) -> IncidentWorkflow:
        with self._lock:
            record = self._require(incident_id)
            assessment = record.analysis.assessment
            reason = execution_block_reason(assessment.requires_approval, record.state)
            if reason:
                # The attempt itself is evidence: record it, then refuse.
                self._audit(
                    record, "execution_blocked", "operator", {"action": action, "reason": reason}
                )
                raise WorkflowError(reason, BLOCKED_MESSAGE[reason])
            self._audit(
                record,
                "execution_requested",
                "operator",
                {"action": action, "mode": "simulated", **({"note": note} if note else {})},
            )
            record.state = "executing"
            record.action = action
            verification = simulation.run(action, assessment.severity)
            record.state = verification.status
            record.verification = verification
            self._audit(
                record,
                "execution_finished",
                "sentinel",
                {"action": action, "state": verification.status},
            )
            self._audit(
                record,
                "verification_recorded",
                "sentinel",
                {
                    "status": verification.status,
                    "success": verification.success,
                    "simulated": True,
                },
            )
            return self._copy(record)

    # -- internals -----------------------------------------------------------

    def _require(self, incident_id: str) -> IncidentWorkflow:
        record = self._records.get(incident_id)
        if record is None:
            raise WorkflowError("incident_not_found", f"No incident with id '{incident_id}'.")
        return record

    def _make_room(self) -> None:
        if len(self._records) < self.capacity:
            return
        for incident_id, record in self._records.items():
            if record.state in TERMINAL_STATES:
                del self._records[incident_id]
                logger.info("evicted finished incident %s", incident_id)
                return
        raise WorkflowError(
            "workflow_store_full",
            (
                f"Workflow store holds {self.capacity} incidents and none of them has "
                "finished. Active incidents are never evicted; this slice keeps state "
                "in memory, so a restart is the reset."
            ),
        )

    def _audit(
        self,
        record: IncidentWorkflow,
        event: str,
        actor: Literal["sentinel", "operator"],
        details: dict[str, Any],
    ) -> None:
        stamp = utc_now()
        record.audit_trail.append(AuditEvent(timestamp=stamp, event=event, actor=actor, details=details))
        record.updated_at = stamp

    def _copy(self, record: IncidentWorkflow) -> IncidentWorkflow:
        return record.model_copy(deep=True)
