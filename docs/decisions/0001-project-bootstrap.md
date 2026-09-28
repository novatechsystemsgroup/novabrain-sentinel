# ADR-0001: Separate Competition Repository

## Status

Accepted

## Date

2026-09-28

## Context

NovaBrain Sentinel is being built as a competition entry for the NVIDIA Build Challenge. The NovaTech ecosystem already includes two relevant repositories:

- **NovaBrain** (`novatech-brain-runtime`) — Intelligence and control-plane source, providing reasoning, memory, and decision models.
- **NovaOps** (`novaops`) — Monitoring and operational source, providing telemetry, observability, and incident data pipelines.

The question arose whether Sentinel should be developed within one of these existing repositories, as a monorepo addition, or as a standalone repository.

## Decision

NovaBrain Sentinel will be maintained as a **separate, standalone public GitHub repository** (`novabrain-sentinel`).

## Rationale

1. **Isolates hackathon development** — Competition work proceeds independently without disrupting the stability or CI/CD pipelines of production-oriented NovaBrain and NovaOps repositories.

2. **Preserves NovaBrain/NovaOps history** — Existing repositories retain their clean commit histories, branch strategies, and release cycles. No hackathon-specific commits pollute their timelines.

3. **Allows selective reuse** — After architectural audit, specific components from NovaBrain and NovaOps can be identified, extracted, and integrated into Sentinel on a case-by-case basis. This is more deliberate than wholesale copying.

4. **Provides a clean public competition repository** — Judges and reviewers see a focused, purpose-built repository that clearly demonstrates the Sentinel concept without extraneous code or unrelated history.

5. **Simplifies deployment and judging** — A single-purpose repository has straightforward setup instructions, clear dependencies, and a focused demo surface. Judges can evaluate Sentinel on its own merits.

## Consequences

- **Positive:**
  - Clean separation of concerns
  - Independent release cadence for competition milestones
  - Clear ownership and scope for the hackathon team
  - Easy to showcase as a standalone product

- **Negative:**
  - Requires explicit effort to identify and integrate reusable components from NovaBrain/NovaOps
  - Potential for temporary code duplication until component extraction is complete
  - Separate CI/CD pipeline must be established

- **Risks:**
  - Component integration may surface architectural mismatches that require refactoring
  - License compatibility must be verified when reusing code from private repositories

## Relationship Model

```
NovaBrain (intelligence/control-plane) ──┐
                                          ├──► Sentinel (competition product)
NovaOps (monitoring/operational) ─────────┘
```

Sentinel integrates reusable components from both sources after architectural audit. It is not a fork or derivative of either repository.
