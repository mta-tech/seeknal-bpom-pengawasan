# Clarification and Ambiguity Policy

**Status:** Active design  
**Scope:** ambiguity handling before execution

---

## 1. Purpose

This document defines when the system must clarify, what kinds of ambiguity matter, and how clarification should operate as a blocking runtime condition.

---

## 2. Clarification Is a Runtime Decision

Clarification is not a stylistic preference.

It is required when materially different interpretations would produce different source paths, filters, entities, or results.

The system must not continue to SQL when that condition holds.

---

## 3. Ambiguity Classes

The system must classify ambiguity into explicit categories.

### 3.1 Entity Ambiguity

The user phrasing does not uniquely determine what is being counted or described.

### 3.2 Business-Event Ambiguity

The user phrase could refer to multiple business events with different counting rules.

### 3.3 Source-Path Ambiguity

More than one plausible authoritative source path remains.

### 3.4 Exact-State vs Family-State Ambiguity

The user phrase may refer either to:

- one exact state,
- or a broader family of states.

### 3.5 Direct-Field vs Discovery Ambiguity

It is not yet clear whether the concept should be answered from a direct field or from structured discovery.

### 3.6 Conversation-Scope Ambiguity

It is not yet clear whether the user is:

- staying on the same topic,
- modifying the previous topic,
- or starting a new topic.

---

## 4. Clarification Threshold

Clarification should be triggered when:

- multiple plausible interpretations remain,
- those interpretations would materially change the query or answer,
- and the user has not already explicitly chosen one.

Clarification should not be triggered for:

- harmless formatting variation,
- obvious typos that do not change meaning,
- or distinctions that do not materially affect the path.

---

## 5. Clarification Style

Clarification must be:

- grounded in the actual ambiguity,
- short,
- specific,
- and framed as alternative interpretations rather than generic requests for more detail.

The system should not ask vague questions like:

- "Can you clarify?"
- "What do you mean?"

It should ask about the unresolved interpretation itself.

---

## 6. Clarification State

When clarification is required, the system must create a pending clarification state containing:

- ambiguity class,
- unresolved term or interpretation,
- topic id,
- candidate options or grounded interpretations,
- and blocking status.

While this state is active, execution must not continue.

---

## 7. Clarification Resolution

When the user answers:

- the response is classified as a clarification response,
- the pending ambiguity is resolved,
- the confirmed interpretation is bound,
- and execution may continue from resolution rather than restarting from scratch.

---

## 8. Clarification Across Follow-Up Turns

Clarification state belongs to a topic.

If the user starts a new topic, the old clarification must not leak into the new one.

If the user stays on the same topic and narrows the interpretation, the resolved binding may carry forward.

---

## 9. Runtime Enforcement Requirement

This policy is not complete unless runtime enforcement exists.

The runtime should block `execute_sql` when:

- pending clarification exists,
- concept binding is incomplete for a material ambiguity,
- cross-system interpretation is unresolved,
- or business event lock is missing.

---

## 10. Refactor Requirements

This design implies:

- `SEEKNAL_ASK.md` must explicitly classify clarification as a first-class turn path,
- `bpom-analyst` must stop before SQL when ambiguity remains,
- runtime ask/response wiring must support suspend/resume behavior,
- and the ledger must carry clarification state explicitly.

