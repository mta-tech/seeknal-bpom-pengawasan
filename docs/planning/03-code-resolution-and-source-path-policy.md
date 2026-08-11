# Code Resolution and Source-Path Policy

**Status:** Active design  
**Scope:** `context/*.md` and resolution behavior before SQL planning

---

## 1. Purpose

This document defines how the agent should decide:

- what kind of concept the user has mentioned,
- which source path is authoritative,
- how codes are resolved,
- and when cross-system differences prevent a naive unified interpretation.

---

## 2. Concept-Type Model

Every relevant user concept must be classified before query planning.

Minimum concept types:

- `Business Event`
- `Coded Classification`
- `Direct Field`
- `Master-Data Attribute`
- `Segment Discovery Concept`
- `Cross-System Asymmetric Concept`
- `Conversation-Scope Reference`

### 2.1 Business Event

Defines what business event is being counted or described.

Examples in abstract form:

- issued state,
- active state,
- submitted state,
- approved lifecycle outcome,
- cancelled lifecycle outcome.

### 2.2 Coded Classification

A concept whose meaning depends on runtime translation from an authoritative code system.

### 2.3 Direct Field

A concept already represented by a direct field and not requiring dictionary translation as its primary path.

### 2.4 Master-Data Attribute

A concept that requires joining a reference or master-data table.

### 2.5 Segment Discovery Concept

A concept whose representation is not guaranteed to be a stable dictionary category and may require controlled discovery.

### 2.6 Cross-System Asymmetric Concept

A concept that exists in multiple systems but does not use the same representation, code, or granularity.

### 2.7 Conversation-Scope Reference

A concept like:

- that same year,
- the same scope,
- that result,
- or now split it by system.

This is resolved from state, not from schema.

---

## 3. Authoritative Source Hierarchy

For each concept, the system must choose a source path from the following hierarchy:

1. stable business semantics
2. dictionary-grounded coded resolution
3. direct field from fact table
4. master-data join
5. structured discovery probe
6. clarification

This hierarchy is not always linear, but one path must emerge as authoritative for the turn.

### 3.1 Stable business semantics

Use when the concept is definitional rather than coded.

### 3.2 Dictionary-grounded resolution

Use when a concept is represented by coded values whose meanings must be resolved from the authoritative dictionary.

### 3.3 Direct field

Use when the concept already maps to an explicit field and should not be over-explored as if it were unknown.

### 3.4 Master-data join

Use when the concept lives in an attached reference structure rather than the main fact table.

### 3.5 Structured discovery

Use when the concept cannot be bound directly and must be discovered from descriptive structure.

### 3.6 Clarification

Use when materially different source paths remain plausible after reasonable resolution attempts.

---

## 4. Dictionary Resolution Policy

Dictionary resolution must be treated as a runtime procedure, not as a static answer store.

The system must support:

- inbound resolution: user concept to candidate code(s),
- outbound resolution: code(s) to answer label(s).

### 4.1 Mandatory discipline

When dictionary-backed resolution applies:

- source-aware filtering must be used,
- system-specific interpretation must be preserved,
- shared numeric codes must not be assumed equivalent across systems,
- bindings must be recorded before SQL is finalized.

### 4.2 What dictionary resolution must not become

It must not become:

- a hidden static mapping list,
- a product-answer shortcut,
- or a justification for skipping concept typing.

---

## 5. Cross-System Asymmetry Policy

When a concept exists in more than one system, the agent must determine whether the systems are:

- equivalent in code and meaning,
- different in code but equivalent in meaning,
- different in code and non-equivalent in granularity,
- or only partially overlapping.

The system must not force false equivalence.

### 5.1 Required behavior

For cross-system asymmetric concepts, the agent must:

1. resolve the concept per system,
2. determine whether the systems can be combined meaningfully,
3. keep limitations visible when they cannot,
4. clarify if the user intent depends on a non-equivalent interpretation.

---

## 6. Direct-Field Protection Rule

If a concept is already anchored by an authoritative direct field, the system must not escalate into uncontrolled discovery unless a real reason exists.

This protects the agent from:

- over-exploration,
- wrong scope drift,
- and polished but semantically wrong answers.

---

## 7. Source-Path Output Requirement

Before final query execution, the skill should be able to state:

- the concept type,
- the authoritative source path,
- any bindings used,
- and whether any cross-system asymmetry remains visible in the result.

---

## 8. Refactor Requirements

This design implies:

- `context/code_translation_protocol.md` remains core and procedural,
- `context/business_glossary.md` must avoid acting like a hidden answer catalog,
- `context/intent_mapping.md` must surface concept typing explicitly,
- and the skill layer must refuse to execute while source-path ambiguity remains unresolved.

