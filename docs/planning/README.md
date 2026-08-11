# seeknal-bpom-neo Planning

This directory contains both:

- the **active design set** for the next refactor, and
- the **historical planning record** that led to the current architecture.

The active design set is the source of truth for ongoing refactor work. Historical planning files remain valuable for audit and reasoning history, but they should no longer be treated as parallel active specifications.

---

## Active Design Set

Use these files as the primary reference for the system to be built:

0. [2026-08-07-routed-context-pages-architecture.md](./2026-08-07-routed-context-pages-architecture.md)
   **Current context architecture.** Replaces the "two large context files read in full every turn"
   model with routed pages opened per question component. Supersedes the access-pattern assumption
   in §3.1 of `2026-06-24-context-simplification-and-followup-protocol.md`, which no longer holds
   now that Gate 2 makes those files blocking reads. Built as variant
   `docs/context_recap/after-chart-route/route-context-070826/`; static checks passed, pilot pending.

1. [2026-06-24-agent-runtime-refactor-master-plan.md](./2026-06-24-agent-runtime-refactor-master-plan.md)
   Consolidated system-wide refactor direction.

2. [2026-06-25-runtime-change-log-and-journaling-requirements.md](./2026-06-25-runtime-change-log-and-journaling-requirements.md)
   Records the runtime changes already applied and the required journaling/state contract.

3. [2026-06-25-forecasting-simplification-note.md](./2026-06-25-forecasting-simplification-note.md)
   Records the simplification of forecasting context and skill while keeping the method deterministic.

4. [01-agent-design-principles.md](./01-agent-design-principles.md)
   Non-negotiable design principles for a dynamic analytical agent.

5. [02-decision-model-and-conversation-state.md](./02-decision-model-and-conversation-state.md)
   Turn classification, semantic commitment, follow-up state, and provenance behavior.

6. [03-code-resolution-and-source-path-policy.md](./03-code-resolution-and-source-path-policy.md)
   Concept typing, authoritative source-path selection, and code resolution policy.

7. [04-clarification-and-ambiguity-policy.md](./04-clarification-and-ambiguity-policy.md)
   Clarification gate, ambiguity classes, and blocking rules before execution.

8. [05-execution-discipline-and-transparency.md](./05-execution-discipline-and-transparency.md)
   Execution control, evidence discipline, reflect blocking, and answer transparency.

---

## Historical Planning Files

The date-stamped planning files from June 2026 remain in this directory for now as historical records.

They are useful for:

- auditing how the design evolved,
- understanding why certain rules were introduced,
- and tracing old regressions or design tradeoffs.

They should **not** be treated as the active design source once the new refactor proceeds.

Historical files currently include:

- `2026-06-03-bpom-neo-context-skill-enhancement.md`
- `2026-06-04-From Query-Centric Reasoning to Information-Centric Reasoning.md`
- `2026-06-04-reasoning-framework-enhancement.md`
- `2026-06-09-decision-operating-system.md`
- `2026-06-11-follow-up-inheritance-refinement.md`
- `2026-06-12-dimension-reasoning-and-data-coverage.md`
- `2026-06-17-dictionary-grounded-code-translation.md`
- `2026-06-17-uat-singleturn-test-suite.md`
- `2026-06-18-llm-forecaster-skill.md`
- `2026-06-19-execution-discipline-and-trust-transparency.md`
- `2026-06-22-clarification-gate-and-grounded-disambiguation.md`
- `2026-06-24-context-simplification-and-followup-protocol.md`

---

## Governance Rule

When a rule appears in both:

- an active design file listed above, and
- a historical planning file,

the active design file wins.

New planning work should extend or amend the active design set rather than adding another date-layered document that duplicates existing architecture decisions.
