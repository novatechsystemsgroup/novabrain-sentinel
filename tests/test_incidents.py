"""Incident analysis endpoint: NVIDIA-backed assessment, policy floor, failure mapping."""

import asyncio
import json
import os

import httpx
import pytest

from sentinel.api import create_app

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
    "likely_causes": ["CPU saturation", "Recent deployment"],
    "recommended_actions": ["Inspect CPU consumers", "Review recent deploys"],
    "requires_approval": False,
    "reasoning_summary": "Latency, errors and CPU rose together, indicating contention.",
}

REASONING = "STEP-BY-STEP CHAIN OF THOUGHT MUST NEVER LEAK"
CONTENT = "FREE TEXT ANSWER MUST NEVER LEAK"

CONFIG = {
    "NVIDIA_API_KEY": "nv-test-key-not-a-real-secret",
    "NVIDIA_BASE_URL": "https://integrate.api.nvidia.com/v1",
    "NVIDIA_MODEL": "nvidia/nemotron-3.5-lightning-30b-a3b",
}


@pytest.fixture(autouse=True)
def provider_config(monkeypatch):
    for key, value in CONFIG.items():
        monkeypatch.setenv(key, value)


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


def request(method: str, path: str, transport, body=None):
    app = create_app(llm_transport=transport)

    async def go():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.request(method, path, json=body)

    return asyncio.run(go())


def post(transport, body=None):
    return request("POST", "/api/v1/incidents/analyze", transport, INCIDENT if body is None else body)


def responder(status=200, payload=None):
    def handler(request):
        return httpx.Response(status, json=payload if payload is not None else tool_call_payload(ASSESSMENT))

    return httpx.MockTransport(handler)


def error_code(response):
    return response.json()["detail"]["error"]


def test_analyze_returns_normalized_assessment():
    response = post(responder())
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"incident_id", "status", "assessment", "model"}
    assert body["status"] == "analyzed"
    assert body["incident_id"].startswith("inc_")
    assert body["model"] == {"provider": "nvidia", "model": CONFIG["NVIDIA_MODEL"]}
    assert set(body["assessment"]) == set(ASSESSMENT)
    assert body["assessment"]["severity"] == "high"
    assert body["assessment"]["confidence"] == 0.87
    assert body["assessment"]["likely_causes"] == ASSESSMENT["likely_causes"]


def test_provider_receives_forced_tool_call_and_real_incident():
    seen = {}

    def handler(request):
        seen.update(json.loads(request.content))
        return httpx.Response(200, json=tool_call_payload(ASSESSMENT))

    post(httpx.MockTransport(handler))
    assert seen["model"] == CONFIG["NVIDIA_MODEL"]
    assert seen["tools"][0]["function"]["name"] == "submit_incident_assessment"
    assert seen["tool_choice"]["function"]["name"] == "submit_incident_assessment"
    user_turn = seen["messages"][-1]["content"]
    assert INCIDENT["title"] in user_turn
    assert "CPU increased to 91%" in user_turn


def test_reasoning_and_free_text_are_never_returned():
    body = post(responder()).text
    assert REASONING not in body
    assert CONTENT not in body


def test_missing_required_field_is_not_filled_in():
    partial = dict(ASSESSMENT)
    del partial["summary"]
    response = post(responder(payload=tool_call_payload(partial)))
    assert response.status_code == 502
    assert error_code(response) == "invalid_model_response"


def test_malformed_tool_arguments_are_rejected():
    def handler(request):
        payload = tool_call_payload(ASSESSMENT)
        payload["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = "{not json"
        return httpx.Response(200, json=payload)

    response = post(httpx.MockTransport(handler))
    assert response.status_code == 502
    assert error_code(response) == "invalid_model_response"


def test_unknown_severity_is_rejected():
    response = post(responder(payload=tool_call_payload({**ASSESSMENT, "severity": "apocalyptic"})))
    assert response.status_code == 502
    assert error_code(response) == "invalid_model_response"


def test_out_of_range_confidence_is_rejected():
    response = post(responder(payload=tool_call_payload({**ASSESSMENT, "confidence": 1.9})))
    assert response.status_code == 502
    assert error_code(response) == "invalid_model_response"


def test_model_answer_without_tool_call_is_not_parsed_from_text():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": CONTENT}}
                ]
            },
        )

    response = post(httpx.MockTransport(handler))
    assert response.status_code == 502
    assert error_code(response) == "invalid_model_response"
    assert CONTENT not in response.text


def test_timeout_maps_to_504():
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    response = post(httpx.MockTransport(handler))
    assert response.status_code == 504
    assert error_code(response) == "provider_timeout"


def test_upstream_http_error_maps_to_502_without_leaking_body():
    def handler(request):
        return httpx.Response(503, text="upstream internals containing details")

    response = post(httpx.MockTransport(handler))
    assert response.status_code == 502
    assert error_code(response) == "provider_unavailable"
    assert "upstream internals" not in response.text


def test_missing_configuration_maps_to_503(monkeypatch):
    for key in os.environ:
        if key.startswith("NVIDIA_"):
            monkeypatch.delenv(key, raising=False)
    response = post(responder())
    assert response.status_code == 503
    assert error_code(response) == "provider_not_configured"
    assert CONFIG["NVIDIA_API_KEY"] not in response.text


@pytest.mark.parametrize(
    "severity, model_requires_approval, expected",
    [
        ("high", False, True),
        ("critical", False, True),
        ("low", False, False),
        ("medium", False, False),
        ("low", True, True),
        ("high", True, True),
    ],
)
def test_approval_policy_floor(severity, model_requires_approval, expected):
    payload = {**ASSESSMENT, "severity": severity, "requires_approval": model_requires_approval}
    body = post(responder(payload=tool_call_payload(payload))).json()
    assert body["assessment"]["requires_approval"] is expected


def test_whitespace_trimmed_and_duplicates_removed():
    payload = {
        **ASSESSMENT,
        "summary": "  padded summary  ",
        "likely_causes": ["  CPU saturation  ", "CPU saturation", "deploy change", "deploy change"],
    }
    body = post(responder(payload=tool_call_payload(payload))).json()
    assert body["assessment"]["summary"] == "padded summary"
    assert body["assessment"]["likely_causes"] == ["CPU saturation", "deploy change"]


def test_long_lists_are_capped():
    payload = {**ASSESSMENT, "recommended_actions": [f"action {i}" for i in range(40)]}
    body = post(responder(payload=tool_call_payload(payload))).json()
    actions = body["assessment"]["recommended_actions"]
    assert 0 < len(actions) <= 12
    assert actions[0] == "action 0"


@pytest.mark.parametrize(
    "broken",
    [
        {"source": "novaops"},
        {**INCIDENT, "title": ""},
        {**INCIDENT, "evidence": "not-a-list"},
        {**INCIDENT, "severity_hint": "definitely-not-a-level"},
    ],
)
def test_request_validation(broken):
    assert post(responder(), body=broken).status_code == 422


def test_valid_minimal_request():
    response = post(responder(), body={"source": "manual", "title": "disk full"})
    assert response.status_code == 200


def test_preserved_routes():
    app = create_app()

    async def go():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            health = await client.get("/health")
            landing = await client.get("/")
            return health, landing

    health, landing = asyncio.run(go())
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "service": "novabrain-sentinel"}
    assert landing.status_code == 200
    assert "NovaBrain Sentinel" in landing.text
