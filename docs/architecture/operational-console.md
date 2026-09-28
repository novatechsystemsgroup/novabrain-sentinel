# Operational Console

`GET /` is the demo console: one page that walks a judge through
`OBSERVE → UNDERSTAND → DECIDE → ACT / REQUEST APPROVAL → VERIFY → LEARN`
without curl, Postman or developer tools. It is three static files served by the same FastAPI
process — no build step, no framework, no CDN, no second container.

```
static/index.html  markup, prefilled demo incident, loop strip, six panels
static/styles.css  dark ops theme on the existing design tokens
static/app.js      fetch + render; the only behaviour on the page
```

The backend is unchanged apart from how it serves them: `/static` is mounted with
`StaticFiles`, and `GET /` returns the file instead of an inline string. No endpoint was added,
removed or altered for the console's sake — the console is a consumer of the same seven routes
the curl examples use.

## The rendering contract

The console deliberately has no opinions:

- **State comes from the response.** Buttons enable off `workflow.state` (`awaiting_approval`
  opens the gate, `approved`/`analyzed` allow execution). `analyzed` only exists when the
  backend decided no gate was needed, so the UI never re-evaluates `requires_approval` to derive
  a second, independent approval policy in JavaScript.
- **Numbers come from the response.** The verification panel prints `verification.before` and
  `verification.after` exactly as delivered. Nothing is recomputed, averaged or improvised in
  the browser.
- **Order comes from the response.** The audit trail renders `audit_trail` in array order.
  There is no `sort` or `reverse` in `app.js`: neighbouring events can share a timestamp, so
  append order is the only sequence that is correct.
- **Labels are the only authored text.** `AUDIT_LABELS` turns backend event names into the
  operator-facing sentences, `ACTION_LABELS` the two action ids into their display names,
  `METRIC_LABELS` the four metric keys into readable units. An unmapped value falls back to
  the raw string rather than being hidden, so a backend addition shows up instead of vanishing.
- **Reasoning stays server-side.** The page renders `reasoning_summary` under the heading
  "Decision rationale". It never reads or references `reasoning_content`, and the backend never
  sends it.

## Honest stage marking

The loop strip marks each stage with a `data-stage-status` attribute and a colour: `real` for
OBSERVE / UNDERSTAND / DECIDE, `mixed` for ACT / REQUEST APPROVAL, `simulated` for VERIFY, and
`planned` for LEARN, whose chip reads "LEARN · not implemented" in its own text. `mixed` exists
because that stage is not one thing: the approval policy and the approval state machine are real,
and only the remediation action is simulated. The chip therefore carries a second line,
"Approval: REAL · Action: SIMULATED", and a two-tone left bar instead of one misleading label. The
legend keys name all four statuses. The real/simulated split is
restated permanently in the footer ("Real NVIDIA inference · Safe simulated remediation") with
the two lists beneath it, so the disclosure survives scrolling past the panels.

## Loading state

Analysis against a live reasoning model takes roughly 7–47 s, so the Run button shows a
spinner, the label "NVIDIA Nemotron is assessing the incident (allow up to 90s)", and the
elapsed whole seconds counted from the request. There is no progress percentage and no
estimated remaining time — the client has no information the server could base one on — and the
assessment, approval, verification and audit panels stay in their empty state until a real
payload arrives. Nothing is drawn optimistically.

## Error handling

`api()` reads the `detail.error` code Sentinel already returns and looks it up in a `NOTICES`
table, so a refusal reads as product language:

| Code | Rendered as |
|---|---|
| `409 approval_required` | "Execution blocked by Sentinel policy" / "Approval is required before this action can run." |
| `409 approval_rejected` | "Execution blocked by Sentinel policy" / a rejection is permanent |
| `409 already_executed` | "Nothing left to execute" |
| `409 invalid_transition` | "That decision is no longer available" |
| `404 incident_not_found` | "Incident not found" — in-memory state, so a restart clears it |
| `503 workflow_store_full` | "Sentinel is at capacity" |
| `503 provider_not_configured` | "Model not configured" |
| `502 provider_unavailable` / `invalid_model_response` | named, with "Sentinel does not patch or invent assessment fields" |
| `504 provider_timeout` | "The model took too long" — 90 s budget, no retry |
| `422` | "The incident details are incomplete" |
| network failure | "Sentinel is unreachable" |

The pre-approval attempt is a first-class demo step, not an error path: `runAction` re-fetches
the incident **before** showing the notice, so the panel already displays the `execution_blocked`
event the backend just audited. Only our own error envelope is parsed; upstream provider bodies,
stack traces and secrets never reach the page.

## Content Security Policy

`GET /` carries:

```
default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self';
img-src 'self' data:; font-src 'self'; object-src 'none'; base-uri 'none';
frame-ancestors 'none'
```

It is attached to that one response, not installed as middleware. The console document is the
only thing that must be locked to its own assets; `/health`, `/docs` and the JSON routes have no
business carrying an HTML-oriented policy, and a middleware would have to special-case them. The
test suite asserts both halves: the console response has exactly these directives with no
`unsafe-inline`/`unsafe-eval`, and the other four response shapes have no CSP header at all.

Because `script-src 'self'` forbids inline script, the page has no `onclick` attributes, no
`<script>` bodies and no `style="…"` attributes; listeners are attached in `start()`.

## Opening an ingested incident

A producer that posts to `POST /api/v1/events/ingest` gets back a relative
`/?incident=<id>` pointer, and the page treats that pointer as client-side routing rather than a
second flow: `start()` reads the query parameter, and when it matches `^inc_[0-9a-f]{32}$` — the
shape Sentinel itself issues — the page fetches `GET /api/v1/incidents/{id}` and renders it into
the panels that already exist. The form fields are then filled from `workflow.event`, so the page
is the evidence of what the producer reported rather than something the operator must retype.
The audit label for the first machine event reads "Operational event ingested".

No new element, route or panel was added for it. The parameter is untrusted text, so a value that
is not an incident id is ignored and the console boots empty; the fetch path has one call site
and no way to be steered off-origin, which is what "the query parameter cannot cause an external
fetch" means in practice. `Clear / New Incident` drops the parameter with `history.replaceState`,
so a reloaded page does not reopen the incident the operator just dismissed. The full contract is
in [machine-event-ingestion.md](machine-event-ingestion.md).

## Drift guards

`tests/test_console.py` pins the console to the backend so a change on one side fails loudly on
the other:

- `ACTION_LABELS` keys must equal `ActionName.__args__`; the action `<select>` offers exactly
  those options, so the UI cannot generate an unknown action.
- `AUDIT_LABELS` keys must equal the events a real `WorkflowStore` emits, collected by driving
  the store rather than by restating a list of strings.
- The severity-hint `<option>` values must equal `SeverityHint.__args__`.
- The prefilled form is parsed out of the HTML with `html.parser`, reconstructed as an
  `IncidentEvent` and validated by pydantic — the demo payload is a real request, not a
  screenshot of one.
- Every `byId("…")` literal in `app.js` must exist as an `id` in `index.html`; every route
  literal must be a documented, same-origin OpenAPI path; no absolute URL and no provider
  hostname appears in any asset.
- Each asset is scanned for `nvapi-`, `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, the provider host,
  `reasoning_content` and chain-of-thought wording.

## Limits

The console adds no authentication, so anyone who can load the page can approve an incident —
the same gap the workflow already documents, now with a friendlier surface. State is per-process,
so the page is only coherent against one replica, and "Clear / New Incident" resets the browser
side only: it does not delete the incident from the store. `LEARN` remains unimplemented and is
marked as such.
