# Machine Event Ingestion

`POST /api/v1/events/ingest` is how an event produced **by another process** enters the
workflow — a monitoring service, an alerting job, or the demo emitter in `scripts/`. The
console and `POST /api/v1/incidents/analyze` stay exactly as they were: a person typing an
incident and a machine reporting one now arrive through different doors and reach the same room.

```
producer (monitoring service / demo emitter)
        │  POST /api/v1/events/ingest  +  Authorization header
        ▼
sentinel/ingestion.py   authenticate the caller → claim the event_id in the ledger
        ▼
        OperationalEvent ──to_incident_event()──▶ IncidentEvent
        ▼
sentinel/analysis.py    analyze_event(...)  — the unchanged OBSERVE → UNDERSTAND → DECIDE leg
        ▼
sentinel/workflow.py    record_analysis(event, analysis, ingest=IngestEvidence(...))
        │               audit: event_ingested → incident_analyzed → approval_requested → …
        ▼
        the same approval gate, the same execute / verify routes, the same console
```

The one-sentence design: **ingestion adds a door and a receipt, not a second workflow.**
`sentinel/nvidia.py` and `sentinel/analysis.py` were not modified for this feature; they cannot
tell a machine-submitted incident from a console-submitted one, which is the point.

## The request contract

`OperationalEvent` (`sentinel/schemas.py`) is the machine-facing shape. It is deliberately
close to what an alerting service already emits, and deliberately has no monitoring-specific
fields Sentinel would not use.

| Field | Required | Rules |
|---|---|---|
| `event_id` | yes | Non-empty producer-stable id. **The idempotency key**, and the only field used for dedup. |
| `source` | yes | What reported it (`novaops`, `uptime-probe`, …). |
| `event_type` | yes | Short machine-readable identifier: `^[a-z][a-z0-9_]{0,63}$`. Open vocabulary — see below. |
| `title` | yes | Becomes `IncidentEvent.title` verbatim (trimmed). |
| `description` | no | `""` when absent. |
| `severity_hint` | no | Producer's guess, `unknown` by default; producer words are aliased — see below. |
| `evidence` | no | Free-text lines; blank and whitespace-only items are dropped. |
| `observed_at` | no | **Timezone-aware** ISO-8601. A naive timestamp is rejected, never guessed at. |

There is no timestamp-free path: when `observed_at` is absent Sentinel records its own receive
time. Both end up in the audit details as `observed_at` / `received_at` — operational metadata,
not model output.

### `event_type` is an open, bounded vocabulary

`vps_offline`, `ssl_expiring`, `ram_high`, `ssd_high`, `docker_stopped` pass through unchanged,
and so does any future identifier that fits the pattern. The five are examples, not an enum:
Sentinel does not interpret `event_type`, it carries it. The bound is structural (length and
character class) so the value survives being echoed into an audit record and a console field
without becoming a place to hide a payload.

### Producer severity words are normalised at the door only

```python
SEVERITY_ALIASES = {"info": "informational", "warning": "medium", "high": "high", "critical": "critical"}
```

`warning → medium` exists because upstream alerting services say "warning" where Sentinel's
`SeverityHint` says `medium`. It is compatibility normalisation for the **incoming vocabulary**,
nothing more. `IncidentEvent.SeverityHint`, the NVIDIA prompt, the approval floor and
`POST /api/v1/incidents/analyze` are untouched by it, and the alias does not decide anything:
`severity_hint` is a hint, and **the NVIDIA assessment still determines actual severity.** A
`warning` event is still `high` if the model says it is, and still lands behind the same
`high`/`critical` approval gate.

## Authentication

One secret, one route: `SENTINEL_INGEST_TOKEN`, presented as `Authorization: Bearer <token>`.

| Condition | HTTP | `detail.error` | Header |
|---|---|---|---|
| `SENTINEL_INGEST_TOKEN` unset or blank | `503` | `ingest_not_configured` | — |
| Header missing, wrong scheme, or value mismatch | `401` | `invalid_ingest_token` | `www-authenticate: Bearer` |

- The comparison is `hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8"))`.
  Both sides are encoded because `compare_digest` raises on non-ASCII `str`, and a raising
  guard would turn a hostile header into a 500.
- The check is a FastAPI **dependency**, so it runs before the body is parsed: an
  unauthenticated caller learns nothing about the event schema (401/503 always precede 422).
- The challenge header is sent for `invalid_ingest_token` only. `503 ingest_not_configured`
  is not an invitation to retry with credentials the deployment does not have.
- The value is never logged, never echoed in a response, never placed in a URL, and never
  reaches `static/`. Log lines on the ingestion path name event ids, not secrets — a test
  fails if any `logger.*` call in `sentinel/*.py` or the emitter puts "token" on a line.

**Scope, stated precisely:** Machine-to-machine ingestion is bearer-token protected. The
public hackathon console remains intentionally unauthenticated. The token guards
`POST /api/v1/events/ingest` and nothing else — `GET /`, `GET /health` and
`POST /api/v1/incidents/analyze` need no credential, and `/analyze` can still trigger paid
inference. Protecting the whole surface is a platform-layer decision (Coolify domain,
Traefik middleware, IP allowlist, internal network), recorded under *Known gaps* in the
README, not something this route quietly claims to have solved.

## Idempotency: `IdempotencyLedger`

A producer that retries on a network timeout would otherwise pay for a second 7–47 s
inference and create a second incident for one event. The ledger answers a single question:
**has this `event_id` already been paid for?**

| Event state | Ledger value | Replay outcome |
|---|---|---|
| Claimed, analysis in flight | `None` | `409 event_in_progress` |
| Finished | the `incident_id` it produced | `200` with `duplicate: true` and the original `incident_id` |
| Unknown | absent | First receipt: claim, analyse, `201` |

- **Bounded and in-process.** A `dict` of at most `MAX_TRACKED_EVENTS = 200` entries behind one
  `threading.Lock`, sized to match `WorkflowStore`. Insertion order is the eviction order, and
  a replay re-inserts the key so a recently used entry is not the next one dropped.
- **A restart clears it.** Idempotency memory is per-process; a redeploy forgets which events
  were already handled, so a producer replaying an event after a restart gets a fresh incident.
  This is documented behaviour of the slice, not a bug to file. It is the reason there is no
  Redis, no table and no queue here: the guarantee is "no duplicate inference within a running
  process", which is what a demo and a single-replica deployment actually need.
- **Claims are never evicted.** At capacity, `_make_room()` takes the oldest *finished* entry.
  If every tracked event is still being analysed, nothing is discarded and the request is
  refused with `503 ingest_ledger_full` — silently dropping an in-flight claim is how a
  duplicate paid inference gets through.
- **The reservation is released on failure.** Any exception from the provider or the store
  (`502`, `504`, `503 provider_not_configured`, `503 workflow_store_full`) unwinds through
  `ledger.release(event_id)`, so the producer can retry the same `event_id` immediately.
- **Stale entries self-heal.** If a finished entry points at an incident the store no longer
  holds (evicted, or cleared by a restart of a differently-ordered process), the entry is
  removed atomically and the event is processed as new. A concurrent racer that finds the same
  staleness degrades to `409 event_in_progress` rather than double-analysing.

## Audit trail

A machine-ingested incident's trail begins one event earlier than a manual one:

```
event_ingested       sentinel  {"event_id":"…","source":"novaops","event_type":"ram_high",
                               "observed_at":"2026-09-28T08:15:00+00:00",
                               "received_at":"2026-09-28T08:15:03.481+00:00"}
incident_analyzed    sentinel  {"severity":"medium","confidence":0.72,…}
approval_requested   sentinel  {…}
```

`observed_at` in the record is always the UTC normalisation of what the producer sent (aware
ISO-8601 in, `+00:00` out) or Sentinel's receive time when the producer sent nothing. The
`event_ingested` details come from `IngestEvidence`, an optional keyword argument on
`record_analysis()`: a manual `/analyze` request files `incident_analyzed` first, because it has
no ingestion metadata to invent.

Everything after `incident_analyzed` is the existing trail from
[approval-workflow.md](approval-workflow.md). **Append order remains authoritative** — nothing
is sorted by timestamp, `WorkflowStore` stays the sole state-transition authority, and there is
no second audit system.

## Response

```json
{
  "event_id": "novaops-evt-2026-09-28-0007",
  "incident_id": "inc_0b86102788ac4420bbeae77574c1a1d2",
  "workflow_state": "awaiting_approval",
  "duplicate": false,
  "console_path": "/?incident=inc_0b86102788ac4420bbeae77574c1a1d2"
}
```

`201 Created` on the first receipt (with `Location` set to the same relative path), `200 OK` on
a replay with `duplicate: true`. The body is a **pointer**, not a copy of the analysis:
`workflow_state` tells the producer where the incident stands, and the full record — event,
assessment, decision, verification, trail — comes from
`GET /api/v1/incidents/{incident_id}`.

`console_path` is relative by design. Sentinel does not know its public hostname, and a
hardcoded absolute URL would break behind any domain, any port mapping and any preview
deployment. A producer that wants a clickable link prefixes its own base URL.

## Console bridge

`/?incident=<id>` opens the same console that produced that link: `start()` reads the query
parameter, and if it is a valid incident id the page fetches
`GET /api/v1/incidents/{id}` and renders it into the existing panels — no new endpoint, no new
markup, no second page. The incident id doubles as the capability: anyone with the URL can read
and act on that incident, which is consistent with the console being unauthenticated.

The parameter is untrusted text, so it is validated against `^inc_[0-9a-f]{32}$` — the shape
Sentinel itself issues — before it is interpolated into a request path. Anything else is
ignored and the page boots in its normal empty state. The consequence tests pin down: **the
query parameter can only ever cause one same-origin fetch of an incident.** There is a single
`fetch(` call site in `app.js` and no way to steer it off-origin, so `/?incident=…` is not an
SSRF gadget and `/?incident=https://example.com` is not a redirect.

`Clear / New Incident` also clears the parameter with `history.replaceState`, so reloading a
dismissed console does not silently reopen the incident the operator just closed.

## Synchronous, and honest about it

The route calls the model and returns. There is no Celery, no queue, no worker pool and no
webhook callback: the producer's HTTP request is held for the **7–47 s** a live Nemotron
analysis takes (measured, see [`docs/evaluation/`](../evaluation/README.md)), with a
`90 s` provider read timeout behind it.

- The client timeout must exceed the backend timeout — `scripts/send_demo_event.py` allows
  `120 s` for exactly this reason.
- A single uvicorn worker still serves other requests concurrently (the wait is `await`ed I/O,
  not a blocked thread), but this endpoint is **not a production-grade high-throughput webhook
  receiver**. It is a synchronous, idempotency-guarded door for a low event rate, which is what
  a monitoring service flagging an offline VPS actually is.
- Any proxy in front of Sentinel needs the same >90 s read timeout documented in
  [`docs/deployment/coolify.md`](../deployment/coolify.md).

## What the endpoint does not expose

Refusal and failure bodies carry a code and a safe sentence
(`{"detail":{"error":"…","message":"…"}}`). Never in a response, log line, or the console:
the ingest token, the `Authorization` header, the NVIDIA key, the provider's raw response body,
`reasoning_content`, or any chain-of-thought text. `422` validation details describe the field
that failed, not the value the producer sent.

## The demo emitter

`scripts/send_demo_event.py` stands in for the upstream producer during the demo. It is stdlib
only (`urllib.request`), reads `SENTINEL_INGEST_TOKEN` from the environment and **refuses to run
without it** (exit `2`, message names the variable, value never printed), takes the target URL
from `--url` (defaulting to `SENTINEL_URL`, then localhost), and accepts **no token flag** — a
secret on a command line lands in shell history.

It posts one NovaOps-shaped event (`source: "novaops"`, `event_type: "ram_high"`,
`severity_hint: "warning"`, three evidence lines) and prints `HTTP <status>`, then the
`event_id`, `incident_id`, `workflow_state`, `duplicate` and `console_path`. Opening the printed
relative path in the browser is the handover from machine to operator.

```bash
export SENTINEL_INGEST_TOKEN=$(openssl rand -hex 32)   # must match the server's value
.venv/bin/python scripts/send_demo_event.py --url http://127.0.0.1:8000
```

**Producer status:** NovaOps is a design reference, not a wired integration. It has
`TriggerAlert(...)` and its outbound transports are a Telegram `http.Post` and
`smtp.SendMail`, both fed pre-rendered text/HTML — there is no machine-readable event to
forward today. The emitter is therefore a *NovaOps-compatible producer*: it speaks the contract
Sentinel accepts, and nothing more should be claimed about it.

## Failure modes

| Condition | HTTP | `detail.error` | Ledger after |
|---|---|---|---|
| Token not configured on the server | `503` | `ingest_not_configured` | untouched (dependency ran first) |
| Missing / malformed / wrong bearer token | `401` | `invalid_ingest_token` | untouched |
| Body fails `OperationalEvent` validation | `422` | pydantic detail | untouched |
| Same `event_id` while its analysis is in flight | `409` | `event_in_progress` | claim intact |
| Ledger full and every entry in flight | `503` | `ingest_ledger_full` | nothing evicted |
| Provider missing, timed out, unreachable, or schema-invalid | `502` / `504` | as in [incident-analysis.md](incident-analysis.md) | claim released |
| Workflow store full of live incidents | `503` | `workflow_store_full` | claim released |

## Testing

`tests/test_ingest.py` drives the real app over `httpx.ASGITransport` with
`httpx.MockTransport` for the provider — mocked HTTP exists only in tests. Coverage: auth
(503 before 401 before 422, `www-authenticate` on 401, wrong-scheme and non-ASCII headers),
normalisation (aliases, the `event_type` pattern accepting a future identifier, aware-vs-naive
`observed_at`, evidence trimming), workflow reuse (machine incidents go through the same gate,
and the pre-approval `409` still blocks execution), idempotency (replay, concurrency, stale
entry, in-progress never evicted, reservation released on provider failure), audit ordering,
response shape and status codes, the emitter's secret handling, and the documentation scope
rules above. `tests/test_console.py` covers the query-parameter bridge.
