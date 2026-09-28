"""Approval gate, execution policy, audit trail and simulated verification."""

import asyncio
import json
from datetime import datetime

import httpx
import pytest

from sentinel.api import create_app
from sentinel.schemas import ActionName
from sentinel.simulation import ACTION_CATALOG
from sentinel.workflow import (
    NON_EVICTABLE_STATES,
    TERMINAL_STATES,
    WorkflowStore,
    execution_block_reason,
)

INCIDENT = {
    "source": "novaops",
    "title": "API latency spike",
    "description": "p95 latency increased from 180ms to 2.4s",
    "severity_hint": "unknown",
    "evidence": ["error rate increased to 8.2%", "CPU increased to 91%"],
}

ASSESSMENT = {
    "summary": "p95 latency spiked 13x alongside an 8.2% error rate.",
    "severity": "high",
    "confidence": 0.87,
    "likely_causes": ["CPU saturation"],
    "recommended_actions": ["Inspect CPU consumers"],
    "requires_approval": False,
    "reasoning_summary": "Latency, errors and CPU rose together, indicating contention.",
}

REASONING = "STEP-BY-STEP CHAIN OF THOUGHT MUST NEVER LEAK"
CONTENT = "FREE TEXT ANSWER MUST NEVER LEAK"
FAKE_KEY = "nv-test-key-not-a-real-secret"

WORKFLOW_KEYS = {
    "incident_id",
    "state",
    "updated_at",
    "event",
    "analysis",
    "approval",
    "action",
    "verification",
    "audit_trail",
}


@pytest.fixture(autouse=True)
def provider_config(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", FAKE_KEY)
    monkeypatch.setenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    monkeypatch.setenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")


def provider_transport(current_assessment):
    def handler(request):
        payload = {
            "id": "chatcmpl-test",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": CONTENT,
                        "reasoning_content": REASONING,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "submit_incident_assessment",
                                    "arguments": json.dumps(current_assessment()),
                                },
                            }
                        ],
                    },
                }
            ],
        }
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


class Sentinel:
    """One app instance, so one in-memory store, driven over several requests."""

    def __init__(self, capacity=50):
        self.assessment = dict(ASSESSMENT)
        self.store = WorkflowStore(capacity=capacity)
        self.app = create_app(
            llm_transport=provider_transport(lambda: self.assessment), store=self.store
        )

    def call(self, method, path, body=None):
        async def go():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self.app), base_url="http://test"
            ) as client:
                return await client.request(method, path, json=body)

        return asyncio.run(go())

    def analyze(self, severity=None, requires_approval=None, event=None):
        if severity:
            self.assessment["severity"] = severity
        if requires_approval is not None:
            self.assessment["requires_approval"] = requires_approval
        response = self.call("POST", "/api/v1/incidents/analyze", event or INCIDENT)
        assert response.status_code == 200, response.text
        return response.json()["incident_id"]

    def workflow(self, incident_id):
        return self.call("GET", f"/api/v1/incidents/{incident_id}")

    def state(self, incident_id):
        return self.workflow(incident_id).json()["state"]

    def trail(self, incident_id):
        return self.workflow(incident_id).json()["audit_trail"]

    def events(self, incident_id):
        return [event["event"] for event in self.trail(incident_id)]

    def approve(self, incident_id, note=None):
        return self.call("POST", f"/api/v1/incidents/{incident_id}/approve", note_body(note))

    def reject(self, incident_id, note=None):
        return self.call("POST", f"/api/v1/incidents/{incident_id}/reject", note_body(note))

    def execute(self, incident_id, action="scale_api_replicas"):
        return self.call("POST", f"/api/v1/incidents/{incident_id}/execute", {"action": action})


def note_body(note):
    return {"note": note} if note else {}


def error_code(response):
    return response.json()["detail"]["error"]


# --- state after analysis -----------------------------------------------------


def test_high_incident_parks_in_awaiting_approval():
    app = Sentinel()
    incident_id = app.analyze(severity="high", requires_approval=False)
    assert app.state(incident_id) == "awaiting_approval"
    assert app.events(incident_id) == ["incident_analyzed", "approval_requested"]


def test_low_incident_is_recorded_as_analyzed():
    app = Sentinel()
    incident_id = app.analyze(severity="low", requires_approval=False)
    assert app.state(incident_id) == "analyzed"
    assert app.events(incident_id) == ["incident_analyzed"]


def test_model_can_still_demand_approval_on_a_low_incident():
    app = Sentinel()
    incident_id = app.analyze(severity="low", requires_approval=True)
    assert app.state(incident_id) == "awaiting_approval"


def test_analyze_response_contract_is_unchanged():
    app = Sentinel()
    body = app.call("POST", "/api/v1/incidents/analyze", INCIDENT).json()
    assert set(body) == {"incident_id", "status", "assessment", "model"}
    assert body["status"] == "analyzed"


def test_workflow_view_returns_every_required_section():
    app = Sentinel()
    incident_id = app.analyze(severity="critical")
    app.approve(incident_id, note="verified against the deploy log")
    app.execute(incident_id)
    body = app.workflow(incident_id).json()
    assert set(body) == WORKFLOW_KEYS
    assert body["event"]["title"] == INCIDENT["title"]
    assert body["event"]["evidence"] == INCIDENT["evidence"]
    assert body["analysis"]["assessment"]["severity"] == "critical"
    assert body["approval"]["decision"] == "approved"
    assert body["approval"]["actor"] == "operator"
    assert body["action"] == "scale_api_replicas"
    assert body["verification"]["success"] is True


# --- the approval gate -------------------------------------------------------


def test_execution_is_blocked_before_approval():
    app = Sentinel()
    incident_id = app.analyze(severity="high")
    response = app.execute(incident_id)
    assert response.status_code == 409
    assert error_code(response) == "approval_required"
    assert app.state(incident_id) == "awaiting_approval"
    assert app.events(incident_id)[-1] == "execution_blocked"


def test_blocked_attempt_is_audited_with_the_attempted_action():
    app = Sentinel()
    incident_id = app.analyze(severity="high")
    app.execute(incident_id, action="restart_api_service")
    blocked = app.trail(incident_id)[-1]
    assert blocked["actor"] == "operator"
    assert blocked["details"]["action"] == "restart_api_service"
    assert blocked["details"]["reason"] == "approval_required"


def test_approval_enables_execution():
    app = Sentinel()
    incident_id = app.analyze(severity="high")
    assert app.approve(incident_id).status_code == 200
    assert app.state(incident_id) == "approved"
    assert app.execute(incident_id).status_code == 200
    assert app.state(incident_id) == "verified"


def test_rejection_blocks_execution_permanently():
    app = Sentinel()
    incident_id = app.analyze(severity="critical")
    assert app.reject(incident_id, note="too risky without a change window").status_code == 200
    assert app.state(incident_id) == "rejected"
    response = app.execute(incident_id)
    assert response.status_code == 409
    assert error_code(response) == "approval_rejected"
    assert app.approve(incident_id).status_code == 409
    assert app.state(incident_id) == "rejected"
    assert app.execute(incident_id).status_code == 409


def test_incident_without_approval_requirement_executes_directly():
    app = Sentinel()
    incident_id = app.analyze(severity="low", requires_approval=False)
    assert app.execute(incident_id).status_code == 200
    assert app.state(incident_id) == "verified"


def test_approve_and_reject_only_apply_to_awaiting_approval():
    app = Sentinel()
    incident_id = app.analyze(severity="low", requires_approval=False)
    assert app.approve(incident_id).status_code == 409
    assert error_code(app.approve(incident_id)) == "invalid_transition"
    assert app.reject(incident_id).status_code == 409
    assert app.state(incident_id) == "analyzed"


def test_invalid_transition_names_the_verb_and_the_state():
    app = Sentinel()
    incident_id = app.analyze(severity="low", requires_approval=False)
    response = app.approve(incident_id)
    assert response.json()["detail"]["message"] == "Cannot approve an incident in state 'analyzed'."
    assert app.reject(incident_id).json()["detail"]["message"] == "Cannot reject an incident in state 'analyzed'."


def test_duplicate_approval_adds_no_audit_event():
    app = Sentinel()
    incident_id = app.analyze(severity="high")
    app.approve(incident_id)
    before = app.events(incident_id)
    assert app.approve(incident_id).status_code == 409
    assert app.events(incident_id) == before


def test_executed_incident_cannot_execute_again():
    app = Sentinel()
    incident_id = app.analyze(severity="high")
    app.approve(incident_id)
    app.execute(incident_id)
    response = app.execute(incident_id)
    assert response.status_code == 409
    assert error_code(response) == "already_executed"


@pytest.mark.parametrize(
    "requires_approval,state,expected",
    [
        (False, "analyzed", None),
        (True, "analyzed", "approval_required"),
        (False, "awaiting_approval", None),
        (True, "awaiting_approval", "approval_required"),
        (False, "approved", None),
        (True, "approved", None),
        (True, "rejected", "approval_rejected"),
        (False, "rejected", "approval_rejected"),
        (False, "executing", "already_executed"),
        (True, "executing", "already_executed"),
        (False, "verified", "already_executed"),
        (True, "verified", "already_executed"),
        (False, "failed", "already_executed"),
        (True, "failed", "already_executed"),
    ],
)
def test_execution_invariant(requires_approval, state, expected):
    assert execution_block_reason(requires_approval, state) == expected


def test_invariant_is_symmetric_with_the_approval_floor():
    # high/critical can never be analysed into an executable state, because the
    # TASK-011 floor forces requires_approval=true and the invariant then blocks.
    app = Sentinel()
    for severity in ("high", "critical"):
        incident_id = app.analyze(severity=severity, requires_approval=False)
        assert app.state(incident_id) == "awaiting_approval"
        assert app.execute(incident_id).status_code == 409


# --- simulation and verification ---------------------------------------------


def test_verification_is_deterministic_and_labelled_simulated():
    app = Sentinel()
    incident_id = app.analyze(severity="high")
    app.approve(incident_id)
    verification = app.execute(incident_id).json()["verification"]
    assert set(verification) == {"status", "simulated", "before", "after", "success"}
    assert verification["status"] == "verified"
    assert verification["simulated"] is True
    assert verification["success"] is True
    assert verification["before"] != verification["after"]


def test_same_action_always_produces_the_same_verification():
    app = Sentinel()
    outcomes = []
    for _ in range(2):
        incident_id = app.analyze(severity="high")
        app.approve(incident_id)
        outcomes.append(app.execute(incident_id).json()["verification"])
    assert outcomes[0] == outcomes[1]


def test_restart_on_critical_incident_fails_verification():
    app = Sentinel()
    incident_id = app.analyze(severity="critical")
    app.approve(incident_id)
    body = app.execute(incident_id, action="restart_api_service").json()
    assert body["state"] == "failed"
    assert body["verification"]["status"] == "failed"
    assert body["verification"]["success"] is False
    assert body["verification"]["after"] == body["verification"]["before"]


def test_failed_verification_is_still_terminal():
    app = Sentinel()
    incident_id = app.analyze(severity="critical")
    app.approve(incident_id)
    app.execute(incident_id, action="restart_api_service")
    assert app.execute(incident_id, action="scale_api_replicas").status_code == 409


def test_action_catalog_is_the_only_executable_surface():
    assert set(ACTION_CATALOG) == set(ActionName.__args__)
    for spec in ACTION_CATALOG.values():
        assert spec.simulated is True
        assert spec.executes is False


def test_unknown_action_is_rejected_before_any_transition():
    app = Sentinel()
    incident_id = app.analyze(severity="high")
    app.approve(incident_id)
    assert app.execute(incident_id, action="delete_production_database").status_code == 422
    assert app.state(incident_id) == "approved"
    assert app.events(incident_id)[-1] == "approval_granted"


# --- audit trail ordering -----------------------------------------------------


def test_audit_trail_order_is_the_authoritative_sequence():
    app = Sentinel()
    incident_id = app.analyze(severity="high")
    app.approve(incident_id, note="go")
    app.execute(incident_id)
    assert app.events(incident_id) == [
        "incident_analyzed",
        "approval_requested",
        "approval_granted",
        "execution_requested",
        "execution_finished",
        "verification_recorded",
    ]


def test_rejection_audit_sequence():
    app = Sentinel()
    incident_id = app.analyze(severity="critical")
    app.reject(incident_id)
    app.execute(incident_id)
    assert app.events(incident_id) == [
        "incident_analyzed",
        "approval_requested",
        "approval_rejected",
        "execution_blocked",
    ]


def test_audit_timestamps_are_non_decreasing():
    app = Sentinel()
    incident_id = app.analyze(severity="high")
    app.approve(incident_id)
    app.execute(incident_id)
    stamps = [datetime.fromisoformat(e["timestamp"]) for e in app.trail(incident_id)]
    assert stamps == sorted(stamps)


def test_every_audit_event_has_the_required_shape_and_a_valid_actor():
    app = Sentinel()
    incident_id = app.analyze(severity="high")
    app.approve(incident_id)
    app.execute(incident_id)
    actors = {event["event"]: event["actor"] for event in app.trail(incident_id)}
    for event in app.trail(incident_id):
        assert set(event) == {"timestamp", "event", "actor", "details"}
        assert event["actor"] in {"sentinel", "operator"}
    assert actors["incident_analyzed"] == "sentinel"
    assert actors["approval_requested"] == "sentinel"
    assert actors["approval_granted"] == "operator"
    assert actors["execution_requested"] == "operator"
    assert actors["execution_finished"] == "sentinel"
    assert actors["verification_recorded"] == "sentinel"


def test_operator_note_is_recorded_in_the_decision_and_the_trail():
    app = Sentinel()
    incident_id = app.analyze(severity="high")
    app.approve(incident_id, note="change window approved by ops")
    body = app.workflow(incident_id).json()
    assert body["approval"]["note"] == "change window approved by ops"
    assert body["audit_trail"][2]["details"]["note"] == "change window approved by ops"


def test_workflow_responses_never_leak_reasoning_or_credentials():
    app = Sentinel()
    incident_id = app.analyze(severity="high")
    approve = app.approve(incident_id, note="go")
    execute = app.execute(incident_id)
    for text in (approve.text, execute.text, app.workflow(incident_id).text):
        assert REASONING not in text
        assert CONTENT not in text
        assert FAKE_KEY not in text


# --- store bounds -------------------------------------------------------------


def test_no_state_outside_terminal_is_evictable():
    assert TERMINAL_STATES == frozenset({"verified", "failed", "rejected"})
    assert NON_EVICTABLE_STATES == frozenset(
        {"analyzed", "awaiting_approval", "approved", "executing"}
    )
    assert not TERMINAL_STATES & NON_EVICTABLE_STATES


def test_store_refuses_to_evict_an_active_incident():
    app = Sentinel(capacity=2)
    first = app.analyze(severity="high")
    second = app.analyze(severity="high")
    response = app.call("POST", "/api/v1/incidents/analyze", INCIDENT)
    assert response.status_code == 503
    assert error_code(response) == "workflow_store_full"
    assert app.state(first) == "awaiting_approval"
    assert app.state(second) == "awaiting_approval"


def test_terminal_incidents_are_evicted_before_active_ones():
    app = Sentinel(capacity=2)
    first = app.analyze(severity="low", requires_approval=False)
    second = app.analyze(severity="high")
    assert app.call("POST", "/api/v1/incidents/analyze", INCIDENT).status_code == 503
    assert app.execute(first).json()["state"] == "verified"
    third = app.analyze(severity="high")
    assert app.workflow(first).status_code == 404
    assert app.state(second) == "awaiting_approval"
    assert app.state(third) == "awaiting_approval"


def test_unknown_incident_is_404_on_every_workflow_route():
    app = Sentinel()
    missing = "/api/v1/incidents/inc_doesnotexist"
    assert app.call("GET", missing).status_code == 404
    for suffix, body in (("approve", {}), ("reject", {}), ("execute", {"action": "scale_api_replicas"})):
        response = app.call("POST", f"{missing}/{suffix}", body)
        assert response.status_code == 404
        assert error_code(response) == "incident_not_found"


def test_each_app_gets_its_own_store():
    first, second = Sentinel(), Sentinel()
    incident_id = first.analyze(severity="high")
    assert incident_id != second.analyze(severity="high")
    assert second.workflow(incident_id).status_code == 404
