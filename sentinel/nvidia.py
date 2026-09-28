"""NVIDIA Build inference client.

Structured output comes from a forced tool call: the model's answer lives in
`tool_calls[0].function.arguments`, never in `content` or `reasoning_content`.
Reading only the validated tool arguments is what keeps chain-of-thought from
reaching an API consumer.
"""

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx

from .schemas import Assessment, IncidentEvent

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
TOOL_NAME = "submit_incident_assessment"

CONNECT_TIMEOUT = 10.0
# Nemotron-3.5-Lightning emits its reasoning before the tool call; live probes
# measured 39-48s end to end, so the read budget has to stay well above that.
READ_TIMEOUT = 90.0
WRITE_TIMEOUT = 30.0
POOL_TIMEOUT = 10.0
MAX_TOKENS = 4096

SYSTEM_PROMPT = (
    "You are NovaBrain Sentinel, an operational incident triage agent. "
    f"You MUST call the {TOOL_NAME} tool with your assessment. "
    "Classify severity from the evidence, not from the reported hint. "
    "recommended_actions are advisory only: never claim to have executed them."
)

_ASSESSMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "One or two sentences describing the incident."},
        "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "likely_causes": {"type": "array", "items": {"type": "string"}},
        "recommended_actions": {"type": "array", "items": {"type": "string"}},
        "requires_approval": {"type": "boolean"},
        "reasoning_summary": {
            "type": "string",
            "description": "Concise 1-3 sentence rationale. Do not include step-by-step reasoning.",
        },
    },
    "required": [
        "summary",
        "severity",
        "confidence",
        "likely_causes",
        "recommended_actions",
        "requires_approval",
        "reasoning_summary",
    ],
}


class ProviderError(Exception):
    code = "provider_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ProviderNotConfigured(ProviderError):
    code = "provider_not_configured"


class ProviderTimeout(ProviderError):
    code = "provider_timeout"


class ProviderUnavailable(ProviderError):
    code = "provider_unavailable"


class InvalidModelResponse(ProviderError):
    code = "invalid_model_response"


@dataclass(frozen=True)
class ProviderConfig:
    api_key: str
    base_url: str
    model: str


def resolve_config() -> ProviderConfig:
    api_key = os.environ.get("NVIDIA_API_KEY", "").strip()
    base_url = os.environ.get("NVIDIA_BASE_URL", "").strip() or DEFAULT_BASE_URL
    model = os.environ.get("NVIDIA_MODEL", "").strip()

    missing = [name for name, value in (("NVIDIA_API_KEY", api_key), ("NVIDIA_MODEL", model)) if not value]
    if missing:
        raise ProviderNotConfigured(f"missing environment configuration: {', '.join(missing)}")
    if not base_url.startswith(("http://", "https://")) or any(c in base_url for c in "[] "):
        raise ProviderNotConfigured("NVIDIA_BASE_URL must be a plain URL such as https://integrate.api.nvidia.com/v1")

    return ProviderConfig(api_key=api_key, base_url=base_url.rstrip("/"), model=model)


def build_user_prompt(event: IncidentEvent) -> str:
    lines = [
        f"source={event.source}",
        f"title={event.title}",
        f"description={event.description or '(none provided)'}",
        f"severity_hint={event.severity_hint}",
    ]
    if event.evidence:
        lines.append("evidence:")
        lines.extend(f"- {item}" for item in event.evidence)
    else:
        lines.append("evidence: (none provided)")
    return "\n".join(lines)


def build_request(config: ProviderConfig, event: IncidentEvent) -> dict[str, Any]:
    return {
        "model": config.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(event)},
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": TOOL_NAME,
                    "description": "Submit the structured operational assessment.",
                    "parameters": _ASSESSMENT_SCHEMA,
                },
            }
        ],
        "tool_choice": {"type": "function", "function": {"name": TOOL_NAME}},
        "temperature": 0.1,
        "top_p": 0.9,
        "max_tokens": MAX_TOKENS,
    }


def parse_assessment(payload: dict[str, Any]) -> Assessment:
    try:
        message = payload["choices"][0]["message"]
        arguments = message["tool_calls"][0]["function"]["arguments"]
        return Assessment.model_validate(json.loads(arguments))
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise InvalidModelResponse("NVIDIA returned no valid structured assessment") from exc


async def analyze_incident(
    event: IncidentEvent,
    *,
    config: ProviderConfig,
    transport: httpx.AsyncBaseTransport | None = None,
) -> Assessment:
    timeout = httpx.Timeout(
        CONNECT_TIMEOUT, read=READ_TIMEOUT, write=WRITE_TIMEOUT, pool=POOL_TIMEOUT
    )
    try:
        async with httpx.AsyncClient(timeout=timeout, transport=transport) as client:
            response = await client.post(
                f"{config.base_url}/chat/completions",
                json=build_request(config, event),
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
    except httpx.TimeoutException as exc:
        raise ProviderTimeout("NVIDIA did not respond within the allowed time") from exc
    except httpx.HTTPError as exc:
        raise ProviderUnavailable("NVIDIA could not be reached") from exc

    if response.status_code != 200:
        raise ProviderUnavailable(f"NVIDIA returned HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise InvalidModelResponse("NVIDIA returned a response that is not JSON") from exc

    return parse_assessment(payload)
