# Incident Analysis

The first implemented stage of the cognitive loop: an operational event goes in, a
validated NVIDIA model assessment comes out.

```
POST /api/v1/incidents/analyze
        │
        ├─ OBSERVE    IncidentEvent is validated by FastAPI/pydantic (422 on bad input)
        ├─ UNDERSTAND sentinel/nvidia.py calls NVIDIA Build with a forced tool call
        │             and validates tool_calls[0].function.arguments into Assessment
        └─ DECIDE     sentinel/analysis.py applies the Sentinel approval policy
        │
        └─→ IncidentAnalysis { incident_id, status, assessment, model }
```

`recommended_actions` are advisory text: the analysis leg itself executes nothing. What
happens after an assessment is filed — the approval gate, the simulated action and the audit
trail — is in [approval-workflow.md](approval-workflow.md).

## Modules

| File | Responsibility | Depends on |
|---|---|---|
| `sentinel/schemas.py` | `IncidentEvent` (request), `Assessment` (model output), `IncidentAnalysis` (response) | pydantic |
| `sentinel/nvidia.py` | environment config, request payload, HTTP call, tool-argument parsing, error taxonomy | `schemas`, `httpx` |
| `sentinel/analysis.py` | the OBSERVE → UNDERSTAND → DECIDE sequence and the approval policy | `schemas`, `nvidia` |
| `sentinel/api.py` | routes and provider-error → HTTP-status mapping | `analysis`, FastAPI |

`nvidia.py` knows nothing about HTTP framing or FastAPI; `api.py` knows nothing about the
provider wire format. The transport is injected (`create_app(llm_transport=...)`) so tests
can substitute `httpx.MockTransport` without touching production code.

## Structured output: forced tool call

The model is `nvidia/nemotron-3.5-lightning-30b-a3b` — a reasoning model that emits its
thinking before answering. Two live probes against NVIDIA Build drove this design:

- Requesting JSON via `response_format` returned HTTP 200 with `finish_reason: length` and
  4168 characters of chain-of-thought in `content` — not parseable JSON.
- Requesting a **forced tool call** (`tool_choice` bound to `submit_incident_assessment`)
  returned `content` of length zero, thinking isolated in `reasoning_content`, and
  schema-valid JSON in `tool_calls[0].function.arguments`.

So the request always declares the `Assessment` fields as a JSON Schema `tools[]` entry and
pins `tool_choice` to that function. `parse_assessment()` reads **only** the tool arguments.

## No gap filling

Every `Assessment` field is required and has no default. If the model omits one, supplies a
malformed value, emits an unknown severity, gives a confidence outside `0.0–1.0`, or answers
in free text without a tool call, the result is `invalid_model_response` (502). Sentinel
never invents a summary, severity, cause, action, confidence or rationale.

The only normalisation applied is presentational and is safe to reverse:

- trimming whitespace from strings and discarding blank ones
- de-duplicating list items, preserving first-seen order
- capping `likely_causes` and `recommended_actions` at 12 items (`MAX_LIST_ITEMS`)

## Approval policy (Sentinel, not the model)

`analysis.py:APPROVAL_FLOOR` is a one-way ratchet:

```python
requires_approval = model_requires_approval or severity in {"high", "critical"}
```

The model may require approval for a `low` or `medium` incident; it may **never** clear the
approval requirement from a `high` or `critical` one. This is a Sentinel policy decision
recorded in the service, separate from the model's own assessment, and it is applied after
the model output has been validated.

## Privacy boundary

- `reasoning_content` is never read, logged, persisted, or returned.
- `content` is never used as a fallback source of assessment fields.
- The response body is built exclusively from validated `Assessment` instances.
- Upstream error bodies are not echoed; a non-200 becomes `NVIDIA returned HTTP <status>`.
- Missing configuration is reported by variable *name* only, never by value.

## Failure modes

| Condition | Exception | HTTP | `detail.error` |
|---|---|---|---|
| `NVIDIA_API_KEY` / `NVIDIA_MODEL` absent, or malformed `NVIDIA_BASE_URL` | `ProviderNotConfigured` | 503 | `provider_not_configured` |
| Read timeout after 90s, connect timeout after 10s | `ProviderTimeout` | 504 | `provider_timeout` |
| Connection failure, or upstream non-200 | `ProviderUnavailable` | 502 | `provider_unavailable` |
| Malformed / missing / schema-invalid tool arguments, non-JSON body | `InvalidModelResponse` | 502 | `invalid_model_response` |
| Request body fails `IncidentEvent` validation | — | 422 | pydantic detail |

Error responses are `{"detail": {"error": "<code>", "message": "<safe text>"}}`.

There is exactly one attempt per request: no retry, no model fallback, no alternate
endpoint. A failed analysis is a failed request.

## Latency (measured, not assumed)

Live runs of the deployed image against `https://integrate.api.nvidia.com/v1` with the
brief's example incident completed in roughly **13–48 seconds**, because the model reasons
before issuing the tool call. Two of those runs are recorded in
[`docs/evaluation/`](../evaluation/README.md).

Consequences for the stack:

- `READ_TIMEOUT = 90.0` in `nvidia.py` — generous on purpose; it is the only guard against a
  hung provider.
- Any reverse proxy in front of Sentinel must allow more than 90s of read time (see
  [`docs/deployment/coolify.md`](../deployment/coolify.md)).
- Clients should set their own timeout above 90s and treat 504 as "retry later", not "bug".
- `GET /health` stays in-process and instant; it never calls the provider, so health checks
  are unaffected by model latency.

## Testing

`tests/test_incidents.py` runs the real FastAPI app over `httpx.ASGITransport` with
`httpx.MockTransport` standing in for NVIDIA Build — mocked HTTP only ever exists in tests.
It covers the normalised response shape, the approval floor, the leak guards, each failure
mapping above, and that `GET /` and `GET /health` still behave as before.
