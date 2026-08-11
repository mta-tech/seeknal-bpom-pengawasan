---
name: bpom-analyst
description: "Analytical BPOM data questions: lock intent, resolve meaning, execute disciplined SQL, and answer from evidence."
tags: [bpom, analyst, reasoning, sql, clarification]
version: "6.2.0"
---

# BPOM Analyst Skill

**Workflow:** `LOAD -> CAPTURE -> CONFIRM -> DISCOVER -> RESOLVE -> PLAN -> EXECUTE -> REFLECT -> GENERATE`

This skill owns workflow and blocking contracts only. Detailed resolver, discovery, and clarification mechanics live in the referenced context files.

## LOAD

Always load:
- `context/business_glossary.md`
- `context/data_quality_rules.md`
- `context/source_discovery_protocol.md`
- `context/code_translation_protocol.md`

Load on demand:
- `context/intent_mapping.md`
- `context/data_architecture.md`
- `context/query_recipes.md`

## CAPTURE

Read the decision frame from `SEEKNAL_ASK.md`.

Produce:
```text
Semantic Commitment Block
State Comparison Result
Topic Identity
```

Decompose the turn into entity, operation, dimensions, conditions, time scope, and output shape.
If the turn is `EXPLAIN_EVIDENCE`, skip to `GENERATE` unless provenance data is missing.

## CONFIRM

Before SQL, produce:
```text
Concept Type Table
Sufficiency Check
```

`Sufficiency Check`:
```text
enough_to_execute:
blocking_ambiguities:
non_blocking_ambiguities:
```

Clarify only when ambiguity would materially change source path, core filters, business event, entity, or result meaning.
If only non-blocking ambiguity remains, execute and state the assumption or limitation briefly.
Budget, stop rules, and no-reask behavior are owned by `SEEKNAL_ASK.md`.

## SOURCE REUSE DECISION

Decide reuse per information-component:
- `REUSE` -> prior validated fact still matches scope
- `DERIVE` -> scope changed or new work is needed
- `DISCARD` -> prior fact exists but scope/binding no longer matches

Reuse prior SQL only when filters, bindings, and scope markers still match the current Semantic Commitment Block.
Read prior validated facts and executed-query references from the journal / database log, not transcript memory.

## DISCOVER

Use `context/source_discovery_protocol.md` when the concept is cross-system, coded but non-exact, segment-like, or missing explicit time/source scope.

Required artifact:
```text
Source Discovery Record
```

Do not write counting SQL while material ambiguity remains.
Do not combine ERBA and ERLA before equivalence has been checked.
If `Sufficiency Check` says execution is already sufficient, stop asking and continue.

## RESOLVE

Run the Four-Pass Resolver from `context/code_translation_protocol.md` for every non-trivial term.

Required artifacts:
```text
Event Lock
TermResolution[]
Binding Matrix
Authoritative Source Path
Resolved Constructs
```

Rules:
- no SQL before these artifacts are stable
- Pass 1 / Pass 2 may bind silently
- Pass 3 / Pass 4 must return to `CONFIRM` with grounded clarification
- no `UNION` before the Binding Matrix is complete with an equivalence verdict
- bindings must come from runtime resolution, not memory

`Resolved Constructs` must summarize source tables, join path, casts, bindings, scope, filters, and shape.

## PLAN

Write a short execution plan from `Resolved Constructs`.
Use `context/query_recipes.md` only after event lock, binding, and source path are stable.

## EXECUTE

- use only the authoritative path selected in `RESOLVE`
- use date ranges, not `EXTRACT`, unless sub-date decomposition truly requires it
- stop once sufficient authoritative evidence has been collected
- do not switch source path because one query failed

## REFLECT

Run `seeknal/skills/evidence-auditor/SKILL.md`.
If audit fails, return to `CONFIRM`, `DISCOVER`, or `RESOLVE`.

## GENERATE

Answer only from committed interpretation and audited evidence.

- every factual statement must trace to executed database evidence or a validated ledger fact
- keep system non-equivalence visible when relevant
- resolve labels before user-facing output when an authoritative label exists
- answer in the user's language
- provenance turns should use stored references before new SQL
