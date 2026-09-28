"""Request and response contracts for incident analysis."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Severity = Literal["low", "medium", "high", "critical"]
SeverityHint = Literal["unknown", "informational", "low", "medium", "high", "critical"]

MAX_LIST_ITEMS = 12


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
