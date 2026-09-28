"""Request and response contracts for incident analysis and the approval workflow."""

from datetime import timezone
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, Field, field_validator

Severity = Literal["low", "medium", "high", "critical"]
SeverityHint = Literal["unknown", "informational", "low", "medium", "high", "critical"]
WorkflowState = Literal[
    "analyzed",
    "awaiting_approval",
    "approved",
    "rejected",
    "executing",
    "verified",
    "failed",
]

MAX_LIST_ITEMS = 12
MAX_NOTE_CHARS = 240

# The whole executable surface. Adding an entry here is the only way to make
# Sentinel able to attempt anything, and every entry is simulated.
ActionName = Literal["scale_api_replicas", "restart_api_service"]

# A machine producer names its own kind of event. Sentinel stores the label and
# never branches on it, so the shape is bounded (safe identifier, length-capped)
# while the vocabulary itself stays the producer's to extend.
EVENT_TYPE_PATTERN = r"^[a-z][a-z0-9_]{0,63}$"

# Producers that speak a severity vocabulary predating Sentinel's own. The alias
# is applied where their words arrive and nowhere else: the hint still never
# decides anything, the NVIDIA assessment still sets the real severity.
SEVERITY_ALIASES = {
    "info": "informational",
    "warning": "medium",
    "high": "high",
    "critical": "critical",
}


class IncidentEvent(BaseModel):
    source: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    severity_hint: SeverityHint = "unknown"
    evidence: list[str] = Field(default_factory=list)


class OperationalEvent(BaseModel):
    """What a machine producer sends: an incident description plus its own key.

    ``event_id`` is the producer's stable identifier and Sentinel's idempotency
    key; ``to_incident_event`` is the only normalisation the analysis path sees.
    Fields Sentinel does not use are ignored rather than rejected, so a real
    producer's extra columns are not a contract failure.
    """

    event_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    event_type: str = Field(pattern=EVENT_TYPE_PATTERN)
    title: str = Field(min_length=1)
    description: str = ""
    severity_hint: SeverityHint = "unknown"
    evidence: list[str] = Field(default_factory=list)
    observed_at: AwareDatetime | None = None

    @field_validator("event_id", "source", "title", "event_type", "description", mode="before")
    @classmethod
    def _trim(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("severity_hint", mode="before")
    @classmethod
    def _alias_producer_severity(cls, value: Any) -> Any:
        if isinstance(value, str):
            lowered = value.strip().lower()
            return SEVERITY_ALIASES.get(lowered, lowered)
        return value

    @field_validator("evidence")
    @classmethod
    def _clean_evidence(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    def to_incident_event(self) -> IncidentEvent:
        return IncidentEvent(
            source=self.source,
            title=self.title,
            description=self.description,
            severity_hint=self.severity_hint,
            evidence=list(self.evidence),
        )

    def observed_at_or(self, received_at: str) -> str:
        """UTC-normalised observation time, falling back to when it arrived.

        A naive timestamp is rejected by the schema rather than assumed to be
        whatever the receiver's clock says.
        """
        if self.observed_at is None:
            return received_at
        return self.observed_at.astimezone(timezone.utc).isoformat()


class IngestEvidence(BaseModel):
    """Operational metadata for the audit trail: who produced this, and when."""

    event_id: str
    source: str
    event_type: str
    observed_at: str
    received_at: str


class IngestResponse(BaseModel):
    """A pointer into the existing workflow, never a second copy of the analysis."""

    event_id: str
    incident_id: str
    workflow_state: WorkflowState
    duplicate: bool
    console_path: str


class Assessment(BaseModel):
    """Model output. Every field must be supplied by the model; nothing is inferred."""

    summary: str = Field(min_length=1)
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    likely_causes: list[str]
    recommended_actions: list[str]
    requires_approval: bool
    reasoning_summary: str = Field(min_length=1)

    @field_validator("summary", "reasoning_summary")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("likely_causes", "recommended_actions")
    @classmethod
    def _clean_items(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            entry = item.strip()
            if entry and entry not in cleaned:
                cleaned.append(entry)
        return cleaned[:MAX_LIST_ITEMS]


class ModelInfo(BaseModel):
    provider: Literal["nvidia"] = "nvidia"
    model: str


class IncidentAnalysis(BaseModel):
    incident_id: str
    status: Literal["analyzed"] = "analyzed"
    assessment: Assessment
    model: ModelInfo


class DecisionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=MAX_NOTE_CHARS)

    @field_validator("note", mode="before")
    @classmethod
    def _blank_is_absent(cls, value: Any) -> Any:
        if isinstance(value, str):
            cleaned = value.strip()
            if len(cleaned) > MAX_NOTE_CHARS:
                raise ValueError(f"note must be at most {MAX_NOTE_CHARS} characters")
            return cleaned or None
        return value


class ExecuteRequest(DecisionRequest):
    action: ActionName


class AuditEvent(BaseModel):
    """One entry in the trail. The append order is the authoritative sequence."""

    timestamp: str
    event: str
    actor: Literal["sentinel", "operator"]
    details: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    actor: Literal["operator"] = "operator"
    decided_at: str
    note: str | None = None


class Verification(BaseModel):
    """Outcome of a simulated action. The metrics are authored constants."""

    status: Literal["verified", "failed"]
    simulated: Literal[True] = True
    before: dict[str, int | float]
    after: dict[str, int | float]
    success: bool


class IncidentWorkflow(BaseModel):
    incident_id: str
    state: WorkflowState
    updated_at: str
    event: IncidentEvent
    analysis: IncidentAnalysis
    approval: ApprovalDecision | None = None
    action: ActionName | None = None
    verification: Verification | None = None
    audit_trail: list[AuditEvent] = Field(default_factory=list)
