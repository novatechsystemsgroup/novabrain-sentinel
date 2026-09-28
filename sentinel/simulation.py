"""The simulated action catalog.

Nothing in this module contacts a system. Each action is a fixed pair of
authored metric snapshots, so the whole ACT/VERIFY leg of the loop is
reproducible without anyone restarting anything.
"""

from typing import Literal

from pydantic import BaseModel

from .schemas import ActionName, Severity, Verification

# The degraded starting point the simulator pretends to observe. Constant, so a
# repeated action always reports the same before/after pair.
DEGRADED = {"api_replicas": 2, "p95_latency_ms": 2400, "error_rate_percent": 8.2, "service_restarts": 0}
SCALED = {"api_replicas": 4, "p95_latency_ms": 610, "error_rate_percent": 0.4, "service_restarts": 0}
RESTARTED = {"api_replicas": 2, "p95_latency_ms": 540, "error_rate_percent": 0.6, "service_restarts": 1}


class SimulatedAction(BaseModel):
    label: str
    description: str
    after: dict[str, int | float]
    # Severities for which this action is modelled as recovering the service.
    recovers_for: frozenset[Severity]
    simulated: Literal[True] = True
    # Explicit, greppable statement that this action performs no real work.
    executes: Literal[False] = False


ACTION_CATALOG: dict[ActionName, SimulatedAction] = {
    "scale_api_replicas": SimulatedAction(
        label="Scale API replicas",
        description=(
            "Adds capacity behind the API service, the usual answer to a latency spike "
            "under CPU saturation. Simulated: no orchestrator is called."
        ),
        after=SCALED,
        recovers_for=frozenset(Severity.__args__),
    ),
    "restart_api_service": SimulatedAction(
        label="Restart API service",
        description=(
            "Recycles the API service. Clears leaked state but does not add capacity, "
            "so it is modelled as insufficient for a critical incident. Simulated."
        ),
        after=RESTARTED,
        recovers_for=frozenset({"low", "medium", "high"}),
    ),
}


def run(action: ActionName, severity: Severity) -> Verification:
    spec = ACTION_CATALOG[action]
    recovered = severity in spec.recovers_for
    return Verification(
        status="verified" if recovered else "failed",
        before=dict(DEGRADED),
        after=dict(spec.after) if recovered else dict(DEGRADED),
        success=recovered,
    )
