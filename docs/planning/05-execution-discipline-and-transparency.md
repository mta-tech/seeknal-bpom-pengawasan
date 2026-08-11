# Execution Discipline and Transparency

**Status:** Active design  
**Scope:** skill execution, evidence audit, and answer trust contract

---

## 1. Purpose

This document defines how the system should behave once a turn has passed:

- turn classification,
- semantic commitment,
- concept typing,
- source-path selection,
- and clarification gating.

It governs:

- when SQL is allowed,
- how much SQL is justified,
- how evidence is audited,
- and how the answer is explained.

---

## 2. Pre-Execution Requirements

No SQL should run until the skill can produce:

- Event Lock
- Concept Type Table
- Binding Table
- Authoritative Source Path
- Output Shape

If any of these are missing for a material part of the question, execution must stop.

---

## 3. Proportional Execution

Execution should be proportional to unresolved information need.

The system should not:

- explore many candidate paths when one authoritative path is already available,
- run many redundant probes after the answerable path is already known,
- or continue searching after valid evidence has already been found and audited.

---

## 4. Authoritative Path Rule

Each answer must be traceable to one chosen authoritative path.

If multiple paths were explored during resolution, only one may become the official path for the answer unless the answer explicitly presents a system-separated comparison.

---

## 5. Reflect as a Blocking Gate

Reflection is not only a post-hoc checklist.

It is a decision gate that must be able to block answer generation.

The reflect step should reject execution outputs when:

- semantic commitment and actual query scope diverge,
- event lock is missing,
- source path remains ambiguous,
- direct-field concepts were mishandled as discovery,
- cross-system non-equivalence was collapsed into one unsupported answer,
- or the final result is internally coherent but semantically wrong for the question.

---

## 6. Limited-Answer Contract

If the full question cannot yet be answered truthfully, the system may produce a limited answer only when:

- the valid subset is clearly identified,
- the missing part is explicitly stated,
- and no fabricated completion is supplied.

This is preferable to a polished wrong answer.

---

## 7. Transparency Contract

Every answer should be explainable through:

- what the system believed the question meant,
- what source path it chose,
- what bindings were used,
- what filters were applied,
- and what evidence was executed.

This does not mean every answer must expose all internals by default. It means the internals must exist and be recoverable.

---

## 8. Provenance Response Mode

When the user requests provenance, the system should answer with:

- executed SQL,
- active filters,
- binding table,
- and scope description

using stored execution evidence where available.

This should not trigger a fresh analytical run unless evidence is missing.

---

## 9. Output Discipline

The answer must not:

- silently broaden scope,
- silently switch entity,
- silently change source path,
- silently translate exact-state questions into family-state answers,
- or omit limitations when a non-equivalence was kept visible.

---

## 10. Refactor Requirements

This design implies:

- `bpom-analyst` must emit stronger internal decision artifacts,
- `evidence-auditor` must be able to block,
- provenance must be ledger-backed,
- and answer trust must come from disciplined execution rather than narrative fluency.

