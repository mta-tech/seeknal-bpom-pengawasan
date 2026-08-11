---
name: evidence-auditor
description: "Audit BPOM analytical evidence before answering. Blocks semantically wrong or unresolved results even when SQL is technically valid."
tags: [bpom, audit, reflection, verification, blocking-gate]
version: "2.1.0"
---

# Evidence Auditor

The auditor decides whether the current reasoning path is safe to answer from.

It is not enough for the SQL to run.
It is not enough for the number to look plausible.
The result must match the committed interpretation and authoritative path.

---

## 1. Inputs

Audit against:

- Semantic Commitment Block
- State Comparison result
- Event Lock
- Concept Type Table
- TermResolution[] and Binding Matrix
- Authoritative Source Path
- Executed evidence

---

## 2. Blocking Checks

### A. Intent and Scope

- Is the entity correct?
- Is the business event explicitly locked?
- Does the chosen date column match the committed event?
- Does the system scope match the committed scope?
- Does the answer shape match the committed output shape?
- Is the per-component reuse verdict (`REUSE` / `DERIVE` / `DISCARD`) consistent with the executed evidence and the prior scope markers? Reused facts must still match the current Semantic Commitment Block.

If not, block and return `RE-RESOLVE` or `RE-SCOPE`.

### B. Source-Path Integrity

- Is there one authoritative source path?
- If multiple paths were explored, was exactly one selected for the answer?
- If the concept was direct-field or master-data based, was unnecessary discovery avoided?
- If the concept was cross-system asymmetric, was false equivalence avoided?
- Was system scope clarified when missing scope would change the answer?

If not, block.

### C. Binding Integrity

- Were coded meanings resolved from runtime authoritative procedure rather than memory?
- Were bindings system-aware where required?
- Was an exact-state question answered with an exact-state binding rather than a family-state collapse?
- Was narrow business meaning proven by discovery when dictionary coverage was broad or partial?
- For every cross-system concept, is there a complete Binding Matrix with an equivalence verdict, and was `UNION` blocked until the matrix was complete?
- Did any binding come from a Pass 3 (semantic) or Pass 4 (empty) result without surfacing a clarification?

If not, block.

### D. Clarification Integrity

- Is there pending clarification state?
- Was a material ambiguity silently collapsed?
- Did execution proceed even though clarification was still required?
- Was missing time/source scope silently defaulted even though it changed the result materially?
- If clarification was triggered by a non-exact `TermResolution`, were all Pass-3 candidates shown grouped by system, ranked by score, and annotated with the meaning-carrier that produced each (per `code_translation_protocol.md` Section 8)?

If yes (or, for the last item, if not), block.

### E. Data Quality Integrity

- `COUNT(DISTINCT ...)` where required?
- correct date range pattern?
- required exclusions present?
- event-specific filters aligned with `data_quality_rules.md`?
- casts and normalization applied when needed?

If not, block.

### F. Honesty Integrity

- Does every number come from executed evidence or a validated ledger fact?
- Was any missing evidence replaced with narrative confidence?
- If the query failed, is the failure visible rather than hidden?

If not, block.

### G. Output Integrity

- Does any raw code appear in user-facing output where an authoritative label is resolvable?
- Were output labels reused from the inbound binding instead of running a redundant outbound dictionary query?

If a raw code appears where a label is resolvable, block and return `RE-RESOLVE` for outbound translation.

---

## 3. Special Guardrails

### 3.1 Technical SQL correctness is not enough

A technically valid query must still fail audit if it represents the wrong interpretation.

### 3.2 Near-miss numbers are still failures

If the reasoning path is wrong but the number is numerically close, treat it as a semantic failure, not a pass.

### 3.3 Limited answers are allowed only when explicit

If only part of the question is safely answerable, the limitation must be visible and the unsupported part must remain unanswered.

---

## 4. Verdicts

- `PASS`
- `RE-RESOLVE`
- `RE-SCOPE`
- `LIMITED_ANSWER`
- `HONEST-FAIL`

Use `PASS` only when:

- the interpretation is stable,
- the source path is authoritative,
- the evidence is audited,
- and no material ambiguity remains.
