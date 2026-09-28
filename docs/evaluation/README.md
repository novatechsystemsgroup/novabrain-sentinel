# Evaluation

Methodology, metrics and results for NovaBrain Sentinel.

## Live inference verification — TASK-011 (2026-09-28)

The first real model run through the shipped artifact. No mocked transport was involved.

| | |
|---|---|
| Image | `novabrain-sentinel:task011` (`docker build` of `main`, non-root UID 10001) |
| Provider | NVIDIA Build, `https://integrate.api.nvidia.com/v1/chat/completions` |
| Model | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| Secret handling | `NVIDIA_API_KEY` injected with `docker run -e` from the shell at run time; never written to disk, never printed |
| Endpoint | `POST /api/v1/incidents/analyze` |
| Input | the brief's example event: `source=novaops`, `title="API latency spike"`, p95 180 ms → 2.4 s, evidence `error rate 8.2%`, `CPU 91%`, `severity_hint=unknown` |

### Results

| Run | `incident_id` | Wall clock | Severity | Confidence | `requires_approval` |
|---|---|---|---|---|---|
| 1 | `inc_0b86102788ac4420bbeae77574c1a1d2` | 12.8 s | `high` | 0.87 | `true` |
| 2 | `inc_1bec63cbae3049ebb0275150a6766c9a` | 47.1 s | `high` | 0.87 | `true` |

Both runs returned HTTP 200 with the full normalised shape
(`incident_id`, `status`, `assessment`, `model`) and all seven assessment fields populated.

Run 1 `reasoning_summary`: *"The combination of sharply increased latency, elevated error
rate, and near-capacity CPU usage indicates a high-impact incident requiring immediate
attention."* — one sentence, a rationale rather than a trace.

### Checks performed on the raw response bodies

- No `reasoning_content` field, and no chain-of-thought text, in either response.
- `severity_hint=unknown` did not anchor the classification: the model raised it to `high`
  from the evidence, which is the behaviour the system prompt asks for.
- The model volunteered `requires_approval=true`; the Sentinel floor would have set it anyway
  for a `high` incident.
- Container log shows `POST /api/v1/incidents/analyze 200 OK` and nothing resembling a key.
- `GET /health` and `GET /` were re-checked against the same image and are unchanged.

### What this tells us

Latency is bimodal for a reasoning model: the same input produced 12.8 s and 47.1 s. A
single-sample benchmark would be misleading, so budget for the tail (`READ_TIMEOUT = 90 s`)
and report ranges. Assessment *quality* was stable across runs; only phrasing and the number
of actions differed.

## Not yet measured

Autonomous remediation, outcome verification and learning are not implemented, so there is
nothing to evaluate for `ACT`, `VERIFY` or `LEARN`.
