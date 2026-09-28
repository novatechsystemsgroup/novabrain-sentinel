# NovaBrain Sentinel

**Persistent Operational AI Agent for the NVIDIA Build Challenge**

NovaBrain Sentinel is an autonomous operational agent that continuously monitors, analyzes, and responds to system events through a structured cognitive loop.

## Core Loop

```
OBSERVE → UNDERSTAND → DECIDE → ACT / REQUEST APPROVAL → VERIFY → LEARN
```

1. **OBSERVE** — Ingest telemetry, logs, metrics, and external signals
2. **UNDERSTAND** — Classify events, detect anomalies, correlate context
3. **DECIDE** — Evaluate response options against policies and risk
4. **ACT / REQUEST APPROVAL** — Execute autonomous remediation or escalate to human operators
5. **VERIFY** — Confirm outcome, measure impact, detect regressions
6. **LEARN** — Update models, refine policies, improve future decisions

## Status

**Early implementation / Hackathon build** — Active development for the NVIDIA competition.

## Architecture

> Architecture documentation will be published here as the system takes shape.

See [`docs/architecture/`](docs/architecture/) for design documents.

## NVIDIA Model Integration

NovaBrain Sentinel leverages NVIDIA AI foundation models and inference endpoints for:

- Event classification and anomaly detection
- Natural language understanding for incident analysis
- Decision reasoning and recommendation generation
- Automated remediation planning

> Integration details will be documented as implementation progresses.

## Deployment

> Deployment documentation will be added as infrastructure is provisioned.

See [`docs/deployment/`](docs/deployment/) for deployment guides.

## Demo

> Demo URL will be published here once the application is deployed.

## Evaluation

> Evaluation methodology, metrics, and results will be documented in [`docs/evaluation/`](docs/evaluation/).

## Security Principles

- **Least privilege** — Minimal permissions for each component
- **Human-in-the-loop** — Critical actions require operator approval
- **Audit trail** — All decisions and actions are logged
- **Secrets management** — No credentials in source code; environment-based configuration
- **Input validation** — All external inputs are validated and sanitized
- **Defense in depth** — Multiple layers of security controls

## Repository Relationship

| Repository | Role |
|---|---|
| **NovaBrain** | Intelligence / control-plane source — reasoning, memory, decision models |
| **NovaOps** | Monitoring / operational source — telemetry, observability, incident data |
| **Sentinel** | Competition product — integrates reusable components from NovaBrain and NovaOps into a unified operational agent |

Sentinel is a separate repository that selectively reuses components from NovaBrain and NovaOps after architectural audit. It is not a fork or copy of either repository.

## License

See [LICENSE](LICENSE).
