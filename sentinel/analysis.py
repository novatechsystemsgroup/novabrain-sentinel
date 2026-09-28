"""OBSERVE → UNDERSTAND → DECIDE for a single operational event."""

from uuid import uuid4

import httpx

from . import nvidia
from .schemas import Assessment, IncidentAnalysis, IncidentEvent, ModelInfo

# Sentinel policy, not a model opinion: the model may raise the approval
# requirement, but it can never lower a high/critical incident below it.
APPROVAL_FLOOR = frozenset({"high", "critical"})


def apply_approval_policy(assessment: Assessment) -> Assessment:
    if assessment.severity in APPROVAL_FLOOR and not assessment.requires_approval:
        return assessment.model_copy(update={"requires_approval": True})
    return assessment


async def analyze_event(
    event: IncidentEvent,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> IncidentAnalysis:
    config = nvidia.resolve_config()
    assessment = await nvidia.analyze_incident(event, config=config, transport=transport)
    return IncidentAnalysis(
        incident_id=f"inc_{uuid4().hex}",
        assessment=apply_approval_policy(assessment),
        model=ModelInfo(model=config.model),
    )
