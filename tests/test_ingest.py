"""Machine event ingestion: bearer auth, normalization, idempotency, audit evidence.

These tests cover the front door only. Everything behind it — the NVIDIA client,
the approval floor, the workflow transitions — is the already-tested path, so the
strongest claim here is that ingestion reaches it unchanged.
"""

import asyncio
import importlib.util
import json
import re
import sys
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from sentinel.api import create_app
from sentinel.ingestion import (
    EventInProgress,
    IdempotencyLedger,
    IngestError,
)
from sentinel.schemas import IncidentEvent, OperationalEvent

ROOT = Path(__file__).resolve().parent.parent

INGEST_PATH = "/api/v1/events/ingest"
TOKEN = "sentinel-test-ingest-token"

CONFIG = {
    "NVIDIA_API_KEY": "nv-test-key-not-a-real-secret",
    "NVIDIA_BASE_URL": "https://integrate.api.nvidia.com/v1",
    "NVIDIA_MODEL": "nvidia/nemotron-3.5-lightning-30b-a3b",
}

# A NovaOps-shaped event: its severity vocabulary is info|warning|high|critical.
MACHINE_EVENT = {
    "event_id": "novaops-evt-0001",
    "source": "novaops",
    "event_type": "ram_high",
    "title": "API latency spike",
    "description": "p95 latency increased from 180ms to 2.4s",
    "severity_hint": "warning",
    "evidence": ["error rate increased to 8.2%", "CPU increased to 91%"],
}

ASSESSMENT = {
    "summary": "p95 latency spiked 13x alongside an 8.2% error rate.",
    "severity": "high",
    "confidence": 0.87,
    "likely_causes": ["CPU saturation"],
    "recommended_actions": ["Review recent deploys"],
    "requires_approval": False,
    "reasoning_summary": "Latency, errors and CPU rose together.",
}

REASONING = "STEP-BY-STEP CHAIN OF THOUGHT MUST NEVER LEAK"
CONTENT = "FREE TEXT ANSWER MUST NEVER LEAK"

MANUAL_INCIDENT = {
    "source": "novaops",
    "title": "API latency spike",
    "description": "p95 latency increased from 180ms to 2.4s",
    "severity_hint": "unknown",
    "evidence": ["error rate increased to 8.2%", "CPU increased to 91%"],
}


@pytest.fixture(autouse=True)
def provider_config(monkeypatch):
    for key, value in CONFIG.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("SENTINEL_INGEST_TOKEN", TOKEN)


def tool_call_payload(arguments):
    return {
        "id": "chatcmpl-test",
        "model": CONFIG["NVIDIA_MODEL"],
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
                                "arguments": json.dumps(arguments),
                            },
                        }
                    ],
                },
            }
        ],
    }


def responder(counts=None, assessment=None):
    """Provider stub that records every call, so 'no second inference' is provable."""

    def handler(request):
        if counts is not None:
            counts.append(json.loads(request.content))
        return httpx.Response(200, json=tool_call_payload(assessment or ASSESSMENT))

    return httpx.MockTransport(handler)


def unreachable_transport():
    def handler(request):
        return httpx.Response(503, text="upstream internals containing details")

    return httpx.MockTransport(handler)


def make_app(transport=None, **overrides):
    return create_app(llm_transport=transport if transport is not None else responder(), **overrides)


def call(app, method, path, body=None, headers=None):
    async def go():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.request(method, path, json=body, headers=headers)

    return asyncio.run(go())


def auth(token=TOKEN):
    return {"Authorization": f"Bearer {token}"}


def ingest(app, body=None, headers=None):
    return call(app, "POST", INGEST_PATH, body=MACHINE_EVENT if body is None else body,
                headers=auth() if headers is None else headers)


def workflow_of(app, incident_id):
    return call(app, "GET", f"/api/v1/incidents/{incident_id}").json()


def audit_events(workflow):
    return [entry["event"] for entry in workflow["audit_trail"]]


def audit_entry(workflow, name):
    return next(entry for entry in workflow["audit_trail"] if entry["event"] == name)


def error_code(response):
    return response.json()["detail"]["error"]


# -- authentication --------------------------------------------------------


def test_unconfigured_ingest_token_refuses_everything(monkeypatch):
    monkeypatch.delenv("SENTINEL_INGEST_TOKEN")
    response = ingest(make_app())
    assert response.status_code == 503
    assert error_code(response) == "ingest_not_configured"
    assert "SENTINEL_INGEST_TOKEN" in response.text


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": ""},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer "},
        {"Authorization": "Token sentinel-test-ingest-token"},
        {"Authorization": "Basic c2VudGluZWw="},
    ],
    ids=["absent", "empty", "scheme-only", "blank-token", "wrong-scheme", "basic"],
)
def test_missing_or_malformed_credentials_are_401(headers):
    response = ingest(make_app(), headers=headers)
    assert response.status_code == 401, response.text
    assert error_code(response) == "invalid_ingest_token"
    assert response.headers.get("www-authenticate") == "Bearer"


def test_wrong_token_is_401_and_echoes_nothing():
    supplied = "guessed-token-should-never-be-echoed"
    response = ingest(make_app(), headers=auth(supplied))
    assert response.status_code == 401
    assert error_code(response) == "invalid_ingest_token"
    assert supplied not in response.text
    assert TOKEN not in response.text
    assert response.headers.get("www-authenticate") == "Bearer"


def test_authorization_is_checked_before_the_body_is_parsed():
    # A caller without the secret must not get a free schema tutorial.
    response = ingest(make_app(), body={}, headers={})
    assert response.status_code == 401, response.text


def test_valid_token_is_accepted_without_any_browser_state():
    response = ingest(make_app())
    assert response.status_code == 201, response.text


def test_token_comparison_is_constant_time():
    source = (ROOT / "sentinel" / "ingestion.py").read_text(encoding="utf-8")
    assert "hmac.compare_digest" in source
    assert "secrets.compare_digest" not in source
    assert "SENTINEL_INGEST_TOKEN" in source


# -- normalization into the existing incident contract ---------------------


def test_machine_event_normalizes_into_the_existing_incident_event():
    event = OperationalEvent(**MACHINE_EVENT)
    incident = event.to_incident_event()
    assert isinstance(incident, IncidentEvent)
    assert incident.source == "novaops"
    assert incident.title == "API latency spike"
    assert incident.description == MACHINE_EVENT["description"]
    assert incident.evidence == MACHINE_EVENT["evidence"]
    # the warning->medium alias is an ingestion concern only
    assert incident.severity_hint == "medium"


def test_ingestion_invents_no_evidence():
    event = OperationalEvent(**{**MACHINE_EVENT, "evidence": [], "description": ""})
    incident = event.to_incident_event()
    assert incident.evidence == []
    assert incident.description == ""


@pytest.mark.parametrize(
    "supplied, expected",
    [
        ("warning", "medium"),
        ("info", "informational"),
        ("high", "high"),
        ("critical", "critical"),
        ("unknown", "unknown"),
        ("medium", "medium"),
        ("low", "low"),
        ("informational", "informational"),
    ],
)
def test_severity_aliases_are_mapped_at_the_ingest_boundary(supplied, expected):
    event = OperationalEvent(**{**MACHINE_EVENT, "severity_hint": supplied})
    assert event.severity_hint == expected


def test_the_alias_reaches_the_provider_as_the_normalized_hint():
    counts = []
    app = make_app(responder(counts))
    ingest(app, body={**MACHINE_EVENT, "severity_hint": "warning"})
    user_turn = counts[0]["messages"][-1]["content"]
    assert "severity_hint=medium" in user_turn
    assert "warning" not in user_turn


def test_aliases_do_not_leak_into_the_manual_contract():
    with pytest.raises(ValidationError):
        IncidentEvent(source="novaops", title="x", severity_hint="warning")
    with pytest.raises(ValidationError):
        IncidentEvent(source="novaops", title="x", severity_hint="info")
    counts = []
    app = make_app(responder(counts))
    assert call(app, "POST", "/api/v1/incidents/analyze", body={**MANUAL_INCIDENT, "severity_hint": "warning"}).status_code == 422


@pytest.mark.parametrize("event_type", ["vps_offline", "ssl_expiring", "ram_high", "ssd_high", "docker_stopped"])
def test_today_novaops_alert_types_pass_unchanged(event_type):
    assert OperationalEvent(**{**MACHINE_EVENT, "event_type": event_type}).event_type == event_type


def test_event_type_stays_extensible_for_future_producers():
    event = OperationalEvent(**{**MACHINE_EVENT, "event_type": "gpu_thermal_throttle"})
    assert event.event_type == "gpu_thermal_throttle"
    counts = []
    app = make_app(responder(counts))
    response = ingest(app, body={**MACHINE_EVENT, "event_type": "gpu_thermal_throttle"})
    assert response.status_code == 201
    assert audit_entry(workflow_of(app, response.json()["incident_id"]), "event_ingested")["details"]["event_type"] == "gpu_thermal_throttle"


@pytest.mark.parametrize(
    "event_type",
    ["", "RAM_HIGH", "ram high", "ram-high", "ram.high", "1ram_high", "ram_high!", "x" * 65],
    ids=["empty", "uppercase", "space", "hyphen", "dot", "leading-digit", "punctuation", "too-long"],
)
def test_event_type_is_a_bounded_safe_identifier(event_type):
    counts = []
    app = make_app(responder(counts))
    assert ingest(app, body={**MACHINE_EVENT, "event_type": event_type}).status_code == 422
    assert counts == [], "an invalid event type must never reach the model"


@pytest.mark.parametrize(
    "broken",
    [
        {k: v for k, v in MACHINE_EVENT.items() if k != "event_id"},
        {**MACHINE_EVENT, "event_id": ""},
        {**MACHINE_EVENT, "event_id": "   "},
        {**MACHINE_EVENT, "source": ""},
        {**MACHINE_EVENT, "title": ""},
        {**MACHINE_EVENT, "event_type": ""},
        {**MACHINE_EVENT, "severity_hint": "definitely-not-a-level"},
        {**MACHINE_EVENT, "evidence": "not-a-list"},
        {**MACHINE_EVENT, "observed_at": "yesterday"},
    ],
    ids=["no-event-id", "empty-event-id", "blank-event-id", "empty-source", "empty-title",
         "empty-event-type", "unknown-severity", "evidence-not-list", "unparsable-observed-at"],
)
def test_machine_event_request_validation(broken):
    counts = []
    app = make_app(responder(counts))
    assert ingest(app, body=broken).status_code == 422
    assert counts == [], "a rejected event must never reach the model"


def test_event_ids_are_trimmed_before_use():
    event = OperationalEvent(**{**MACHINE_EVENT, "event_id": "  novaops-evt-0002  "})
    assert event.event_id == "novaops-evt-0002"


def test_unknown_fields_are_ignored_not_rejected():
    # A real producer carries columns Sentinel does not use; the contract must not
    # fail because of them, and must not store them either.
    event = OperationalEvent(**{**MACHINE_EVENT, "vps_id": 42, "vps_name": "lon-3"})
    assert not hasattr(event, "vps_id")
    counts = []
    app = make_app(responder(counts))
    assert ingest(app, body={**MACHINE_EVENT, "vps_id": 42}).status_code == 201


# -- observed_at is operational metadata ----------------------------------


def test_naive_observed_at_is_rejected_not_guessed():
    with pytest.raises(ValidationError):
        OperationalEvent(**{**MACHINE_EVENT, "observed_at": "2026-09-28T10:00:00"})


def test_observed_at_is_normalized_to_utc_for_the_audit_trail():
    app = make_app()
    response = ingest(app, body={**MACHINE_EVENT, "observed_at": "2026-09-28T10:15:00+02:00"})
    details = audit_entry(workflow_of(app, response.json()["incident_id"]), "event_ingested")["details"]
    assert details["observed_at"] == "2026-09-28T08:15:00+00:00"


def test_absent_observed_at_becomes_the_receive_time():
    app = make_app()
    response = ingest(app, body={k: v for k, v in MACHINE_EVENT.items() if k != "observed_at"})
    details = audit_entry(workflow_of(app, response.json()["incident_id"]), "event_ingested")["details"]
    assert details["observed_at"] == details["received_at"]
    assert details["received_at"].endswith("+00:00")


# -- workflow: one path, real gate, audit evidence ------------------------


def test_machine_ingested_trail_starts_with_event_ingested():
    app = make_app()
    body = ingest(app).json()
    workflow = workflow_of(app, body["incident_id"])
    assert audit_events(workflow) == ["event_ingested", "incident_analyzed", "approval_requested"]
    entry = workflow["audit_trail"][0]
    assert entry["actor"] == "sentinel"
    assert set(entry["details"]) == {"event_id", "source", "event_type", "observed_at", "received_at"}
    assert entry["details"]["event_id"] == MACHINE_EVENT["event_id"]
    assert entry["details"]["source"] == "novaops"


def test_machine_event_runs_the_existing_analysis_and_approval_policy():
    app = make_app()
    body = ingest(app).json()
    workflow = workflow_of(app, body["incident_id"])
    assert body["workflow_state"] == "awaiting_approval"
    assert workflow["state"] == "awaiting_approval"
    assert workflow["analysis"]["assessment"]["severity"] == "high"
    assert workflow["analysis"]["assessment"]["requires_approval"] is True
    assert workflow["analysis"]["model"]["model"] == CONFIG["NVIDIA_MODEL"]
    assert workflow["event"]["severity_hint"] == "medium"


def test_high_severity_model_assessment_forces_the_gate_even_when_the_model_says_no():
    counts = []
    app = make_app(responder(counts, {**ASSESSMENT, "severity": "critical", "requires_approval": False}))
    assert ingest(app).json()["workflow_state"] == "awaiting_approval"


def test_low_severity_machine_event_lands_in_analyzed():
    app = make_app(
        responder(assessment={**ASSESSMENT, "severity": "low", "requires_approval": False})
    )
    body = ingest(app).json()
    assert body["workflow_state"] == "analyzed"
    assert audit_events(workflow_of(app, body["incident_id"])) == ["event_ingested", "incident_analyzed"]


def test_the_gate_still_blocks_execution_for_a_machine_event():
    app = make_app()
    incident_id = ingest(app).json()["incident_id"]
    blocked = call(app, "POST", f"/api/v1/incidents/{incident_id}/execute",
                   body={"action": "scale_api_replicas", "note": "producer pushed too hard"})
    assert blocked.status_code == 409
    assert error_code(blocked) == "approval_required"
    # The refusal is answered with the reason; the evidence of the attempt lives
    # on the incident, which is what the console reloads.
    events = audit_events(workflow_of(app, incident_id))
    assert events[0] == "event_ingested"
    assert events[-1] == "execution_blocked"


def test_a_machine_event_can_be_approved_and_executed_from_the_console_path():
    app = make_app()
    incident_id = ingest(app).json()["incident_id"]
    assert call(app, "POST", f"/api/v1/incidents/{incident_id}/approve", body={"note": "ok"}).status_code == 200
    executed = call(app, "POST", f"/api/v1/incidents/{incident_id}/execute",
                    body={"action": "scale_api_replicas", "note": "go"})
    assert executed.status_code == 200
    assert executed.json()["state"] == "verified"
    assert audit_events(executed.json())[-2:] == ["execution_finished", "verification_recorded"]


def test_manual_analyze_trail_does_not_invent_ingest_metadata():
    app = make_app()
    analysis = call(app, "POST", "/api/v1/incidents/analyze", body=MANUAL_INCIDENT).json()
    workflow = workflow_of(app, analysis["incident_id"])
    assert audit_events(workflow) == ["incident_analyzed", "approval_requested"]
    assert "event_ingested" not in audit_events(workflow)


# -- response contract ----------------------------------------------------


def test_ingest_response_is_a_reference_not_a_second_copy_of_the_analysis():
    response = ingest(make_app())
    body = response.json()
    assert set(body) == {"event_id", "incident_id", "workflow_state", "duplicate", "console_path"}
    assert "assessment" not in body and "event" not in body
    assert body["duplicate"] is False
    assert body["event_id"] == MACHINE_EVENT["event_id"]
    assert response.status_code == 201


def test_console_path_is_relative_and_points_at_the_loaded_incident():
    response = ingest(make_app())
    path = response.json()["console_path"]
    assert path == f"/?incident={response.json()['incident_id']}"
    assert not path.startswith(("http://", "https://", "//"))
    assert response.headers["location"] == path


def test_reasoning_and_free_text_never_cross_the_ingest_boundary():
    counts = []
    response = ingest(make_app(responder(counts)))
    assert REASONING not in response.text
    assert CONTENT not in response.text
    assert TOKEN not in response.text


# -- idempotency ----------------------------------------------------------


def test_first_receipt_calls_the_provider_once_and_a_replay_not_at_all():
    counts = []
    app = make_app(responder(counts))
    first = ingest(app)
    second = ingest(app)
    assert first.status_code == 201
    assert second.status_code == 200
    assert len(counts) == 1
    replay = second.json()
    assert replay["duplicate"] is True
    assert replay["incident_id"] == first.json()["incident_id"]
    assert replay["console_path"] == first.json()["console_path"]
    assert replay["workflow_state"] == first.json()["workflow_state"]


def test_a_replay_reports_the_live_workflow_state():
    app = make_app()
    incident_id = ingest(app).json()["incident_id"]
    call(app, "POST", f"/api/v1/incidents/{incident_id}/reject", body={"note": "known flapping"})
    replay = ingest(app).json()
    assert replay["duplicate"] is True
    assert replay["workflow_state"] == "rejected"


def test_concurrent_duplicate_waits_instead_of_paying_for_a_second_inference():
    counts = []

    async def handler(request):
        counts.append(1)
        if len(counts) == 1:
            await hold.wait()
        return httpx.Response(200, json=tool_call_payload(ASSESSMENT))

    hold = asyncio.Event()
    app = create_app(llm_transport=httpx.MockTransport(handler))

    async def go():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = asyncio.create_task(
                client.post(INGEST_PATH, json=MACHINE_EVENT, headers=auth())
            )
            while not counts:
                await asyncio.sleep(0.01)
            second = await client.post(INGEST_PATH, json=MACHINE_EVENT, headers=auth())
            hold.set()
            return await first, second

    accepted, in_progress = asyncio.run(go())
    assert accepted.status_code == 201
    assert in_progress.status_code == 409
    assert error_code(in_progress) == "event_in_progress"
    assert in_progress.headers.get("www-authenticate") is None
    assert len(counts) == 1


def test_a_failed_inference_releases_the_event_for_retry():
    state = {"broken": True}
    counts = []

    def handler(request):
        counts.append(1)
        if state["broken"]:
            return httpx.Response(503, text="upstream internals")
        return httpx.Response(200, json=tool_call_payload(ASSESSMENT))

    app = create_app(llm_transport=httpx.MockTransport(handler))
    failed = ingest(app)
    assert failed.status_code == 502
    assert error_code(failed) == "provider_unavailable"
    state["broken"] = False
    retried = ingest(app)
    assert retried.status_code == 201
    assert retried.json()["duplicate"] is False
    assert len(counts) == 2


def test_a_timeout_also_releases_the_event():
    state = {"first": True}

    def handler(request):
        if state["first"]:
            state["first"] = False
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, json=tool_call_payload(ASSESSMENT))

    app = create_app(llm_transport=httpx.MockTransport(handler))
    assert ingest(app).status_code == 504
    state["first"] = False
    assert ingest(app).status_code == 201


def test_invalid_model_output_releases_the_event():
    state = {"first": True}

    def handler(request):
        payload = tool_call_payload(ASSESSMENT)
        if state["first"]:
            payload["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = "{not json"
            state["first"] = False
        return httpx.Response(200, json=payload)

    app = create_app(llm_transport=httpx.MockTransport(handler))
    assert ingest(app).status_code == 502
    assert ingest(app).status_code == 201


def test_provider_is_never_called_when_the_event_is_not_analyzed():
    counts = []
    app = make_app(responder(counts))
    assert ingest(app, body={**MACHINE_EVENT, "event_type": "not an identifier"}).status_code == 422
    assert ingest(app, headers={}).status_code == 401
    assert counts == []


def test_idempotency_memory_is_in_process_only():
    counts = []
    event = {**MACHINE_EVENT, "event_id": "novaops-evt-restart"}
    first = ingest(make_app(responder(counts)))
    second = ingest(make_app(responder(counts)), body=event)
    assert first.status_code == second.status_code == 201
    assert second.json()["duplicate"] is False
    assert len(counts) == 2


def test_a_stale_ledger_entry_for_a_forgotten_incident_is_reprocessed():
    store_ledger = IdempotencyLedger()
    store_ledger.reserve("novaops-evt-0001")
    store_ledger.complete("novaops-evt-0001", "inc_forgotten")
    app = create_app(llm_transport=responder(), store=None, ingest_ledger=store_ledger)
    first = ingest(app)
    assert first.status_code == 201
    assert first.json()["duplicate"] is False
    assert first.json()["incident_id"].startswith("inc_")
    assert store_ledger.reserve("novaops-evt-0001") == first.json()["incident_id"]


def test_the_ledger_evicts_only_finished_events():
    ledger = IdempotencyLedger(capacity=2)
    assert ledger.reserve("ev-live") is None
    ledger.complete("ev-done-1", "inc_1")
    ledger.complete("ev-done-2", "inc_2")
    assert ledger.reserve("ev-done-1") == "inc_1"
    assert ledger.reserve("ev-new") is None
    assert ledger.reserve("ev-done-2") is None, "the oldest finished event was evicted"


def test_a_full_ledger_fails_loudly_instead_of_dropping_an_in_flight_event():
    ledger = IdempotencyLedger(capacity=1)
    assert ledger.reserve("ev-busy") is None
    response = ingest(make_app(ingest_ledger=ledger), body={**MACHINE_EVENT, "event_id": "ev-next"})
    assert response.status_code == 503
    assert error_code(response) == "ingest_ledger_full"
    with pytest.raises(EventInProgress):
        ledger.reserve("ev-busy")


def test_ledger_rejects_a_non_positive_capacity():
    with pytest.raises(ValueError):
        IdempotencyLedger(capacity=0)


def test_ledger_release_is_idempotent_and_only_clears_its_own_reservation():
    ledger = IdempotencyLedger()
    ledger.reserve("ev-a")
    ledger.release("ev-a")
    ledger.release("ev-a")
    assert ledger.reserve("ev-a") is None
    assert ledger.reserve("ev-b") is None
    ledger.complete("ev-b", "inc_b")
    ledger.release("ev-b")
    assert ledger.reserve("ev-b") == "inc_b", "release must not undo a finished event"


# -- the ingest error surface --------------------------------------------


def test_ingest_errors_carry_documented_status_codes():
    from sentinel.ingestion import INGEST_ERROR_STATUS

    assert INGEST_ERROR_STATUS == {
        "invalid_ingest_token": 401,
        "ingest_not_configured": 503,
        "event_in_progress": 409,
        "ingest_ledger_full": 503,
    }
    assert issubclass(IngestError, Exception)


def test_provider_errors_are_unchanged_by_ingestion(monkeypatch):
    assert ingest(make_app(unreachable_transport())).status_code == 502
    monkeypatch.delenv("NVIDIA_API_KEY")
    assert error_code(ingest(make_app())) == "provider_not_configured"


def test_ingest_is_a_machine_route_the_console_never_calls():
    assert INGEST_PATH in create_app().openapi()["paths"]
    console = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    assert "events/ingest" not in console, (
        "the browser must not be able to reach the machine-to-machine front door"
    )


# -- the demo producer ----------------------------------------------------


def emitter_module():
    path = ROOT / "scripts" / "send_demo_event.py"
    assert path.exists(), "scripts/send_demo_event.py is missing"
    spec = importlib.util.spec_from_file_location("send_demo_event", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_demo_emitter_is_novops_compatible_not_novops():
    source = (ROOT / "scripts" / "send_demo_event.py").read_text(encoding="utf-8")
    assert "demo" in source.lower()
    assert "NovaOps-compatible" in source
    assert "SENTINEL_INGEST_TOKEN" in source
    assert "--token" not in source, "the token must never be a CLI argument"
    assert not re.search(
        r"(?:print|write|exit|log)[^\n]*\btoken\b", source, re.I
    ), "the token value must never reach the printed output"


def test_demo_emitter_budget_is_above_the_provider_read_timeout():
    source = (ROOT / "scripts" / "send_demo_event.py").read_text(encoding="utf-8")
    timeouts = [int(value) for value in re.findall(r"timeout\s*=\s*(\d+)", source)]
    assert timeouts and max(timeouts) >= 120


def test_demo_emitter_builds_a_valid_machine_event():
    module = emitter_module()
    event = module.build_event("fixed-event-id")
    assert OperationalEvent(**event).event_id == "fixed-event-id"
    assert event["source"] == "novaops"
    assert event["severity_hint"] == "warning"


def test_demo_emitter_refuses_to_run_without_a_token(monkeypatch, capsys):
    monkeypatch.delenv("SENTINEL_INGEST_TOKEN", raising=False)
    module = emitter_module()
    with pytest.raises(SystemExit) as exit_info:
        module.main(["--url", "http://127.0.0.1:9"])
    assert exit_info.value.code != 0
    captured = capsys.readouterr()
    assert "SENTINEL_INGEST_TOKEN" in captured.err + captured.out
    assert TOKEN not in captured.err + captured.out


# -- honest documentation scope ------------------------------------------

DOC_PATHS = (
    "README.md",
    "docs/architecture/machine-event-ingestion.md",
    "docs/decisions/0003-machine-event-ingestion.md",
    "docs/deployment/coolify.md",
    "docs/evaluation/README.md",
    ".env.example",
)

FORBIDDEN_AUTH_CLAIMS = (
    "every endpoint requires authentication",
    "all endpoints are protected",
    "the console requires a token",
    "protects the whole application",
    "globally protected",
    "the api is authenticated",
    "authenticated console",
)

CANONICAL_SCOPE_SENTENCE = "Machine-to-machine ingestion is bearer-token protected"


@pytest.mark.parametrize("relative", DOC_PATHS)
def test_docs_never_overstate_what_the_token_protects(relative):
    text = (ROOT / relative).read_text(encoding="utf-8").lower()
    for claim in FORBIDDEN_AUTH_CLAIMS:
        assert claim not in text, f"{relative} claims {claim!r}"


@pytest.mark.parametrize("relative", ["README.md", "docs/architecture/machine-event-ingestion.md", "docs/decisions/0003-machine-event-ingestion.md"])
def test_docs_state_the_scope_and_the_unauthenticated_console(relative):
    text = (ROOT / relative).read_text(encoding="utf-8")
    assert CANONICAL_SCOPE_SENTENCE in text
    assert "unauthenticated" in text
    assert "/api/v1/events/ingest" in text
    assert "SENTINEL_INGEST_TOKEN" in text
    assert "restart" in text.lower() and "idempot" in text.lower()


def test_docs_document_the_ingest_contract_and_the_synchronous_limit():
    text = (ROOT / "docs/architecture/machine-event-ingestion.md").read_text(encoding="utf-8")
    for token in ("event_ingested", "event_id", "event_type", "observed_at", "www-authenticate", "hmac.compare_digest"):
        assert token in text, f"missing {token}"
    assert "synchronous" in text.lower()
    assert "409" in text and "401" in text and "503" in text


def test_env_example_names_the_token_without_valuing_it():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "SENTINEL_INGEST_TOKEN=" in text
    assert not re.search(r"SENTINEL_INGEST_TOKEN=\s*\S", text)


TOKEN_ASSIGNMENT = re.compile(r"SENTINEL_INGEST_TOKEN\s*=\s*(?![<$])([^\s\"';#]{12,})")
BEARER_LITERAL = re.compile(r"Bearer\s+(?![<$])([A-Za-z0-9._\-]{12,})")


@pytest.mark.parametrize("relative", [*DOC_PATHS, "Dockerfile", "static/app.js", "static/index.html"])
def test_no_credential_shaped_text_in_shipped_files(relative):
    text = (ROOT / relative).read_text(encoding="utf-8")
    assert "nvapi-" not in text
    assert not TOKEN_ASSIGNMENT.search(text), f"{relative} assigns a real-looking token"
    assert not BEARER_LITERAL.search(text), f"{relative} carries a literal bearer token"


def test_shipped_python_never_logs_the_ingest_token():
    offenders = []
    for path in [*(ROOT / "sentinel").glob("*.py"), ROOT / "scripts" / "send_demo_event.py"]:
        source = path.read_text(encoding="utf-8")
        for line in source.splitlines():
            if re.search(r"\b(logger|logging)\.(info|warning|error|debug)\(", line) and "token" in line.lower():
                offenders.append(f"{path.name}: {line.strip()}")
    assert not offenders, f"a token may appear in a log line: {offenders}"
