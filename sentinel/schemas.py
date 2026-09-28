"""Request and response contracts for incident analysis and the approval workflow."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

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


class IncidentEvent(BaseModel):
    source: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    severity_hint: SeverityHint = "unknown"
    evidence: list[str] = Field(default_factory=list)


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
