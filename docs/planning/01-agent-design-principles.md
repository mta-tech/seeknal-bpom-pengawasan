# Agent Design Principles

**Status:** Active design  
**Scope:** Whole BPOM analytical agent runtime

---

## 1. Objective

The BPOM agent must be designed as a **dynamic analytical runtime** that reasons from data conditions and authoritative sources, not from memorized product-specific patterns.

The system must know:

- what the user is asking,
- what type of concept is being referenced,
- which source path is authoritative,
- whether clarification is required,
- and how to retain conversation continuity without inheriting wrong reasoning.

---

## 2. Non-Negotiable Principles

### 2.1 Anti-Hardcode

The system must not be improved by embedding:

- question-specific answers,
- product-name-specific shortcut mappings as the primary operating method,
- static answer catalogs,
- or ever-growing sets of example-driven SQL rules.

Allowed teaching method:

- concept classes,
- decision rules,
- source-path selection,
- code resolution procedure,
- clarification discipline,
- follow-up discipline,
- transparency discipline.

### 2.2 Method Over Memory

The system should know **how to derive** an answer, not **what the likely answer is**.

### 2.3 One Meaning Must Come from One Authoritative Path

For any user concept, the agent must identify the most authoritative source path available and use that path consistently.

It must not mix:

- dictionary interpretation,
- direct-field interpretation,
- discovery interpretation,
- and master-data interpretation

without an explicit reason.

### 2.4 Clarify Before Compute

If materially different interpretations remain possible, the system must clarify before executing SQL.

### 2.5 Inherit Answers, Re-derive Methods

Across turns, the system may inherit:

- validated facts,
- active scope,
- user-confirmed bindings.

It must re-derive:

- columns,
- filters,
- source path,
- code resolution,
- and query logic.

### 2.6 Conditions Over Product Names

The active architecture must be expressed in terms of:

- concept classes,
- data conditions,
- source asymmetry,
- event semantics,
- direct-field vs coded-field behavior.

Named product families may exist in audit, evaluation, and historical documents, but should not define the active reasoning model.

---

## 3. Architectural Principles

### 3.1 Thin Orchestrator

`SEEKNAL_ASK.md` should remain the conversation-level orchestrator only.

It should not carry:

- product segment catalogs,
- schema detail,
- code lists,
- or long domain examples.

### 3.2 Purified Context Layer

`context/*.md` should contain:

- stable facts,
- resolution procedures,
- data quality rules,
- query frameworks.

It should not become an answer monolith.

### 3.3 Blocking Skill Workflow

Skills must not merely suggest good behavior. They must be structured so that unresolved ambiguity or missing bindings block execution.

### 3.4 Runtime Clarification Contract

Clarification must be a real runtime state, not only an instruction in prose.

### 3.5 Single Active Design Source

There must be a compact active design set. Historical planning may remain archived, but must not compete with the active system specification.

---

## 4. What This Means in Practice

The system should improve by becoming better at:

- locking the business event,
- classifying concepts,
- choosing the correct source,
- detecting non-equivalence across systems,
- handling follow-up state,
- explaining provenance.

The system should not improve by becoming better at:

- remembering more named examples,
- storing more product-specific shortcuts,
- or accumulating more giant planning documents with overlapping instructions.

---

## 5. Refactor Implications

These principles imply the following:

- `SEEKNAL_ASK.md` must shrink and focus.
- `context/` must be reorganized by role.
- `bpom-analyst` must gain harder pre-execution gates.
- `evidence-auditor` must become a blocking semantic gate.
- historical planning must stop acting as active architecture.

