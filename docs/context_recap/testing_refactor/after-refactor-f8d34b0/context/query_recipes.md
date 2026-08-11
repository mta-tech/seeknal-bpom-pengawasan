# Query Recipes — Adaptive SQL Frameworks

Recipes are execution frameworks, not understanding tools.
Use them only after:

- entity is locked,
- business event is locked,
- time scope is locked,
- source scope is locked,
- and code/discovery binding is stable.

## Global rules

- Use date ranges, not `EXTRACT`, for year scoping.
- If time scope is missing and would materially change the answer, clarify first.
- Resolve codes to labels after runtime binding.
- For combined-system work, cast and filter each side correctly before any `UNION`.
- Do not substitute forecast tables for factual historical counts.

## Core recipe families

These recipe families are examples of execution shapes.
They are not the full universe of valid BPOM questions.

### R1 — Issued-identity count

Use when the event is an issued identity or active registration-style question and source scope is already locked.

### R2 — Submission / application count

Use when the event is a submission/application-style question and source scope is already locked.

### R3 — Cross-system combined count

Use only after verifying that:

- the concept exists in both systems,
- the business meaning is equivalent enough to combine,
- and the user actually wants a combined result.

### R4 — Breakdown / ranking

Before grouping:

- verify dimension coverage,
- verify code translation path,
- avoid low-coverage presentation columns when a more stable coded dimension exists.

### R5 — Commitment / lifecycle outcome

Lock first whether the user asks about:

- issued identities that also have a commitment state,
- or records whose lifecycle reached that state.

Do not reuse the same filter stack for both.
