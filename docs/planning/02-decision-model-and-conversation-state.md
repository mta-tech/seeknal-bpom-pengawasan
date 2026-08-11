# Decision Model and Conversation State

**Status:** Active design  
**Scope:** `SEEKNAL_ASK.md` and conversation-level runtime behavior

---

## 1. Purpose

This document defines how the agent should interpret each turn before any domain resolution or SQL execution begins.

It defines:

- turn classification,
- semantic commitment,
- follow-up state handling,
- conversation ledger behavior,
- and provenance behavior.

---

## 2. Turn Classification

Every user turn must first be classified into one of the following:

- `SMALL_TALK`
- `META`
- `OUT_OF_SCOPE`
- `PROVENANCE`
- `CLARIFICATION_RESPONSE`
- `DATA_QUESTION`

This classification must happen before any deep reasoning.

### 2.1 DATA_QUESTION

A turn is a data question only when the user is requesting new analysis or a new fact that requires the schema or a validated ledger fact.

### 2.2 PROVENANCE

A turn is provenance when the user asks:

- where the number came from,
- what query was used,
- which filter was applied,
- how the result was calculated.

Provenance must not trigger new SQL if the necessary evidence already exists in the ledger.

### 2.3 CLARIFICATION_RESPONSE

A turn is a clarification response when the user is resolving a pending ambiguity introduced by the system in the immediately active topic.

---

## 3. Semantic Commitment Block

Before source resolution begins, the system must lock a semantic commitment block:

- `Entity`
- `Operation`
- `Dimensions`
- `Conditions`
- `Time Scope`
- `Output Shape`

This block is the working interpretation of the turn.

It is not yet the SQL plan. It is the semantic frame that the SQL plan must satisfy.

### 3.1 Why this block is mandatory

Without this block, the system risks:

- counting the wrong entity,
- using the wrong date column,
- answering at the wrong altitude,
- over-expanding scope,
- or inheriting the wrong previous interpretation.

---

## 4. Conversation State Model

After semantic commitment is drafted, the system must compare the new turn against the active conversation state.

The result must be one of:

- `NEW_QUESTION`
- `MODIFY_SCOPE`
- `EXTEND_SCOPE`
- `EXPLAIN_EVIDENCE`

### 4.1 NEW_QUESTION

Use when:

- the entity changes,
- the core business event changes,
- the concept family changes materially,
- or the user clearly starts a different topic.

### 4.2 MODIFY_SCOPE

Use when:

- the topic stays the same,
- but one or more scope parameters change,
- such as year, system, exact category, or exact status.

### 4.3 EXTEND_SCOPE

Use when:

- the same core topic remains,
- but the user asks for a broader view,
- a breakdown,
- a comparison,
- or an additional dimension.

### 4.4 EXPLAIN_EVIDENCE

Use when:

- the necessary validated fact already exists,
- and the user is asking for explanation, SQL, filter logic, or a summary from existing facts.

---

## 5. Topic Identity

Conversation state must distinguish between:

- current topic identity,
- prior topic identity,
- and topic reset.

The system must not assume that every follow-up remains on the same topic.

Indicators of topic shift include:

- a changed business event,
- a changed entity family,
- a changed analysis intent,
- or an explicit user reset such as "different question now".

---

## 6. Conversation Ledger

The conversation ledger should store:

- active topic id,
- active scope,
- established facts,
- explicit user-confirmed bindings,
- pending clarification state,
- provenance references.

It should not store:

- cached reasoning as authoritative truth,
- assumed filters as permanent facts,
- implicit method choices as reusable decisions.

### 6.1 What may be inherited

- validated answers,
- explicit user-confirmed scope,
- explicit user-confirmed interpretation,
- provenance references to prior execution.

### 6.2 What must be re-derived

- source path,
- code binding logic,
- column choices,
- filter logic,
- query shape,
- system-combination behavior.

---

## 7. Provenance Contract

Provenance is not a new data question.

When provenance is requested, the system should answer from the ledger and execution record using:

- the executed SQL,
- the binding table,
- active filters,
- and the semantic commitment summary for that answer.

No new SQL should run unless the required evidence is actually missing.

---

## 8. Refactor Requirements

This design implies:

- `SEEKNAL_ASK.md` must explicitly own turn classification and state comparison,
- provenance must become a first-class gate,
- topic identity must be explicit,
- ledger structure must be minimal but strict,
- and follow-up handling must be defined by scope logic, not by ad hoc reuse of prior reasoning.

